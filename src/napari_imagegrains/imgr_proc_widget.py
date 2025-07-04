import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from typing import TYPE_CHECKING
from pathlib import Path
import webbrowser
import shutil
import torch

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QVBoxLayout, QTabWidget, QPushButton,
                            QWidget, QFileDialog,  QLineEdit, QGroupBox,
                            QHBoxLayout, QGridLayout, QLabel, QCheckBox,
                            QProgressBar, QRadioButton, QMessageBox, QScrollArea)
from superqt import QLabeledSlider
from qtpy.QtWidgets import QSizePolicy
from magicgui.widgets import create_widget

from imagegrains.segmentation_helper import eval_set, predict_single_image #keep_tif_crs, map_preds_to_imgs
from imagegrains import data_loader, plotting #after imagegrains v2: __cp_version__

from cellpose import models, io, core, version
from napari_matplotlib.base import NapariMPLWidget

import pandas as pd
import numpy as np
import requests

from .folder_list_widget import FolderList
from .utils import find_match_in_folder, compute_average_ap

if TYPE_CHECKING:
    import napari


class ImageGrainProcWidget(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer

        self.image_path = None

        # specifies whether current perf plot is for a dataset or a single image
        self.performance_plot_type = None
        self.mAP = None

        # Main widget and layout
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)

        self.tabs = QTabWidget()
        scroll.setWidget(self.tabs)

        # Mute dialog box notifications 
        self.supress_notifications = False

        # Main layout of your widget
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(scroll)

        # segmentation tab
        self.segmentation = QWidget()
        self._segmentation_layout = QVBoxLayout()
        self.segmentation.setLayout(self._segmentation_layout)
        self.tabs.addTab(self.segmentation, 'Segmentation')

        self.check_download_model = QCheckBox('Download model')
        self.check_download_model.setChecked(False)
        self._segmentation_layout.addWidget(self.check_download_model)

        ### Elements "Model download" ###
        self.model_download_group = VHGroupModel('Model download', orientation='G')
        self.model_download_group.toggle_visibility('invisible')
        self._segmentation_layout.addWidget(self.model_download_group.gbox)

        ##### Elements "Download models" #####
        self.lbl_select_model_for_download = QLabel("Model URL")
        self.btn_goto_zenodo = QPushButton("Zenodo")
        self.btn_goto_zenodo.setToolTip("Go to https://zenodo.org/")
        self.repo_model_path_display = QLineEdit("No URL")
        self.lbl_select_directory_for_download = QLabel("Download model to directory")
        # self.local_directory_model_path_display = QLineEdit("No local path")
        self.local_directory_model_path_display = create_widget(value=Path("No local path"), options={"mode": "d", "label": "Choose a directory"})
        self.btn_download_model = QPushButton("Download model")
        self.btn_download_model.setToolTip("Add URL to model repo and click to download models")

        self.model_download_group.glayout.addWidget(self.lbl_select_model_for_download, 0, 0, 1, 1)
        self.model_download_group.glayout.addWidget(self.btn_goto_zenodo,  0, 1, 1, 1)
        self.model_download_group.glayout.addWidget(self.repo_model_path_display,  0, 2, 1, 1)
        self.model_download_group.glayout.addWidget(self.lbl_select_directory_for_download, 1, 0, 1, 1)
        # self.model_download_group.glayout.addWidget(self.local_directory_model_path_display,  1, 1, 1, 1)
        self.model_download_group.glayout.addWidget(self.local_directory_model_path_display.native,  1, 1, 1, 2)
        self.model_download_group.glayout.addWidget(self.btn_download_model, 2, 0, 1, 3)

        label_widget = QLabel('<a href="https://github.com/dmair1989/imagegrains/blob/main/notebooks/4_train_cellpose_model.ipynb">To train your own model check here</a>')
        label_widget.setTextFormat(Qt.RichText)
        label_widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label_widget.setOpenExternalLinks(True)
        #label_widget.native.setStyleSheet("QLabel { color : blue; }")
        self.model_download_group.glayout.addWidget(label_widget, 3, 0, 1, 3)


        ### Elements "Model selection" ###
        self.model_selection_group = VHGroup('Model selection', orientation='G')
        self._segmentation_layout.addWidget(self.model_selection_group.gbox)

        ##### Elements "Select model folder" #####
        self.btn_select_model_folder = QPushButton("Select model folder")
        self.model_selection_group.glayout.addWidget(self.btn_select_model_folder, 0, 0, 1, 2)

        ##### Elements "Model list" #####
        self.model_list = FolderList(viewer, file_extensions=None)
        self.model_selection_group.glayout.addWidget(self.model_list, 1, 0, 1, 2)


        ### Elements "Image selection"
        self.image_group = VHGroup('Image selection', orientation='G')
        self._segmentation_layout.addWidget(self.image_group.gbox)
        self.btn_select_image_folder = QPushButton("Select image folder")
        self.btn_select_image_folder.setToolTip("Select Image Folder")
        self.image_group.glayout.addWidget(self.btn_select_image_folder)

        ##### Elements "Image list" #####
        self.image_list = FolderList(viewer, file_extensions=['.png', '.jpg', '.jpeg', '.tif', '.tiff'])
        self.image_group.glayout.addWidget(self.image_list)


        ### Single image segmentation
        self.single_image_segmentation_group = VHGroup('Single image segmentation', orientation='G')
        self._segmentation_layout.addWidget(self.single_image_segmentation_group.gbox)

        ##### Run segmentation on current image button #####
        self.btn_run_segmentation_on_single_image = QPushButton("Run segmentation on selected image")
        self.btn_run_segmentation_on_single_image.setToolTip("Run segmentation on current image")
        self.single_image_segmentation_group.glayout.addWidget(self.btn_run_segmentation_on_single_image)

        ##### Save manually processed mask button
        self.btn_save_manually_processed_mask = QPushButton("Save manually processed mask")
        self.btn_save_manually_processed_mask.setToolTip("Save manually processed mask")
        self.single_image_segmentation_group.glayout.addWidget(self.btn_save_manually_processed_mask)

        ##### Directory for manually processed masks
        self.man_proc_directory = create_widget(value=Path("No local path"), options={"mode": "d", "label": "Choose a directory"})
        self.single_image_segmentation_group.glayout.addWidget(QLabel("Save manually processed mask to"))
        self.single_image_segmentation_group.glayout.addWidget(self.man_proc_directory.native)


        ### Elements "Segmentation options" ###
        self.segmentation_option_group = VHGroup('Segmentation options', orientation='G')
        self._segmentation_layout.addWidget(self.segmentation_option_group.gbox)

        self.radio_segment_jpgs = QRadioButton('Segment .jpg')
        self.radio_segment_jpgs.setChecked(True)
        self.segmentation_option_group.glayout.addWidget(self.radio_segment_jpgs, 0, 0, 1, 1)
        self.radio_segment_pngs = QRadioButton('Segment .png')
        self.segmentation_option_group.glayout.addWidget(self.radio_segment_pngs, 1, 0, 1, 1)
        self.radio_segment_tiffs = QRadioButton('Segment .tif')
        self.segmentation_option_group.glayout.addWidget(self.radio_segment_tiffs, 2, 0, 1, 1)

        self.check_use_gpu = QCheckBox('Use GPU')
        self.segmentation_option_group.glayout.addWidget(self.check_use_gpu, 0, 1, 1, 1)
        self.check_save_mask = QCheckBox('Save prediction(s)')
        self.segmentation_option_group.glayout.addWidget(self.check_save_mask, 1, 1, 1, 1)
        self.check_load_saved_prediction_mask = QCheckBox('Load prediction(s)')
        self.segmentation_option_group.glayout.addWidget(self.check_load_saved_prediction_mask, 2, 1, 1, 1)

        self.pred_directory = create_widget(value=Path("No local path"), options={"mode": "d", "label": "Choose a directory"})
        self.segmentation_option_group.glayout.addWidget(QLabel("Save prediction(s) to"), 3, 0, 1, 1)
        self.segmentation_option_group.glayout.addWidget(self.pred_directory.native, 3, 1, 1, 2)

        self.check_change_diameter = QCheckBox('Expected median diameter (px)')
        self.check_change_diameter.setChecked(False)
        self.segmentation_option_group.glayout.addWidget(self.check_change_diameter, 0, 2, 1, 1)

        self.qls_expected_median_diameter = QLabeledSlider(Qt.Horizontal)
        self.qls_expected_median_diameter.setRange(7, 1000)
        self.qls_expected_median_diameter.setValue(17)
        self.qls_expected_median_diameter.setFixedWidth(200)
        self.qls_expected_median_diameter.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.expected_median_diameter = self.qls_expected_median_diameter.value()
        self.qls_expected_median_diameter.setVisible(False)
        self.segmentation_option_group.glayout.addWidget(self.qls_expected_median_diameter, 1, 2, 1, 1)

        self.check_use_georef = QCheckBox('Use georeferencing (requires GDAL)')
        self.check_use_georef .setChecked(False)
        self.segmentation_option_group.glayout.addWidget(self.check_use_georef, 2, 2, 1, 1)


        ### Elements "Run segmentation" ###
        self.folder_segmentation_group = VHGroup('Folder segmentation', orientation='G')
        self._segmentation_layout.addWidget(self.folder_segmentation_group.gbox)
        self.btn_run_segmentation_on_folder = QPushButton("Run segmentation on image folder")
        self.btn_run_segmentation_on_folder.setToolTip("Run segmentation on entire folder")
        self.folder_segmentation_group.glayout.addWidget(self.btn_run_segmentation_on_folder)

        self.lbl_segmentation_progress = QLabel("Segmentation progress")
        self.folder_segmentation_group.glayout.addWidget(self.lbl_segmentation_progress)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.folder_segmentation_group.glayout.addWidget(self.progress_bar)



        # performance tab
        self.options_tab = QWidget()
        self._options_tab_layout = QVBoxLayout()
        self.options_tab.setLayout(self._options_tab_layout)
        self.tabs.addTab(self.options_tab, 'Performance')

        self.perf_folder_group = VHGroup('Folders', orientation='G')
        self._options_tab_layout.addWidget(self.perf_folder_group.gbox)

        self.perf_pred_directory = create_widget(value=Path("No local path"), options={"mode": "d", "label": "Choose a directory"})
        self.perf_mask_directory = create_widget(value=Path("No local path"), options={"mode": "d", "label": "Choose a directory"})
        self.perf_folder_group.glayout.addWidget(QLabel("Pick predictions folder"), 0, 0, 1, 1)
        self.perf_folder_group.glayout.addWidget(self.perf_pred_directory.native, 0, 1, 1, 1)
        self.perf_folder_group.glayout.addWidget(QLabel("Pick mask folder"), 1, 0, 1, 1)
        self.perf_folder_group.glayout.addWidget(self.perf_mask_directory.native, 1, 1, 1, 1)
        self.perf_folder_group.gbox.setMaximumHeight(self.perf_folder_group.gbox.sizeHint().height())


        ### Plotting
        self.perf_plotting_group = VHGroup('Plotting', orientation='G')
        self._options_tab_layout.addWidget(self.perf_plotting_group.gbox)

        self.mpl_widget = NapariMPLWidget(viewer)
        self.axes = self.mpl_widget.canvas.figure.subplots()
        self.perf_plotting_group.glayout.addWidget(self.mpl_widget.canvas, 0, 0, 1, 2)
        self.btn_compute_performance_single_image = QPushButton("Compute performance single image")
        self.perf_plotting_group.glayout.addWidget(self.btn_compute_performance_single_image, 1, 0, 1, 1)
        self.btn_compute_performance_folder = QPushButton("Compute performance folder")
        self.perf_plotting_group.glayout.addWidget(self.btn_compute_performance_folder, 2, 0, 1, 1)
        self.btn_save_average_precision = QPushButton("Save average precision")
        self.perf_plotting_group.glayout.addWidget(self.btn_save_average_precision, 1, 1, 1, 1)
        self.btn_save_performance_plot = QPushButton("Save performance plot")
        self.perf_plotting_group.glayout.addWidget(self.btn_save_performance_plot, 2, 1, 1, 1)
        self.btn_save_performance_plot.setToolTip("Save performance plot")
        
        #### Options
        self.perf_options_group = VHGroup('Options', orientation='G')
        self._options_tab_layout.addWidget(self.perf_options_group.gbox)

        self.qtext_mask_str = QLineEdit("_mask")
        self.perf_options_group.glayout.addWidget(QLabel("Mask string"), 0, 0, 1,1)
        self.perf_options_group.glayout.addWidget(self.qtext_mask_str, 0, 1, 1, 1)

        self.qtext_pred_str = QLineEdit("_pred")
        self.perf_options_group.glayout.addWidget(QLabel("Prediction string"), 1, 0, 1,1)
        self.perf_options_group.glayout.addWidget(self.qtext_pred_str, 1, 1, 1, 1)

        self.perf_options_group.gbox.setMaximumHeight(self.perf_options_group.gbox.sizeHint().height())


        self.add_connections()


    def add_connections(self):
        '''Connects GUI elements with execution functions.'''

        self.check_download_model.stateChanged.connect(self._on_check_toggle_visibility)
        self.btn_goto_zenodo.clicked.connect(self._on_click_goto_zenodo)
        self.btn_download_model.clicked.connect(self._on_click_download_model)
        self.image_list.currentItemChanged.connect(self._on_select_image)
        self.model_list.currentItemChanged.connect(self._on_select_model)
        self.btn_select_image_folder.clicked.connect(self._on_click_select_image_folder)
        self.btn_select_model_folder.clicked.connect(self._on_click_select_model_folder)
        self.btn_run_segmentation_on_single_image.clicked.connect(self._on_click_segment_single_image)
        self.btn_save_manually_processed_mask.clicked.connect(self._on_click_save_manually_processed_mask)
        self.btn_run_segmentation_on_folder.clicked.connect(self._on_click_segment_image_folder)
        self.btn_compute_performance_single_image.clicked.connect(self._on_click_compute_performance_single_image)
        self.btn_compute_performance_folder.clicked.connect(self._on_click_compute_performance_folder)
        self.btn_save_average_precision.clicked.connect(self._on_save_average_precision)
        self.btn_save_performance_plot.clicked.connect(self._on_save_performance_plot)
        self.qls_expected_median_diameter.valueChanged.connect(self._on_slider_change)
        self.check_change_diameter.stateChanged.connect(self._on_check_toggle_visibility)


    def _on_click_goto_zenodo(self):
        """Opens a zenodo record"""

        zenodo_url = "https://zenodo.org/records/15309323"
        webbrowser.open(zenodo_url)


    def _on_click_download_model(self):
        """Downloads models from Github or Zenodo"""

        if self.repo_model_path_display.text() == "No URL":
            return False

        if self.local_directory_model_path_display.value == "No local path":
             return False 
        
        self.model_url_user = self.repo_model_path_display.text()
        if "github.com" in self.model_url_user:
            self.model_url_processed = self.model_url_user.replace("github.com", "raw.githubusercontent.com").replace("blob/", "")
            self.model_name = (self.model_url_processed.split("/")[-1])
            self.model_save_path = self.local_directory_model_path_display.value
            content_in_bytes = requests.get(str(self.model_url_processed)).content
            assert type(content_in_bytes) is bytes
            with open(str(Path(self.model_save_path).joinpath(self.model_name)), 'wb') as f_out:
                f_out.write(content_in_bytes)
       
        elif "zenodo.org" in self.model_url_user:
            self.model_save_path = self.local_directory_model_path_display.value
            self.model_url_processed = self.model_url_user
            self.model_name = (self.model_url_processed.split("/")[-1].split("?")[0])
            self.model_save_path = self.local_directory_model_path_display.value
            content_in_bytes = requests.get(str(self.model_url_processed)).content
            assert type(content_in_bytes) is bytes
            with open(str(Path(self.model_save_path).joinpath(self.model_name)), 'wb') as f_out:
                f_out.write(content_in_bytes)
            
            # if several models should be downloaded from zenodo at a time:
            # self.model_file_extension = ".260325"
            # try:
            #     response = requests.get(self.model_url_processed)
            #     response.raise_for_status()
            # except requests.exceptions.RequestException as e:
            #     print(f"{e}")

            # data = response.json()
            # files = data.get("files", [])

            # for file in files:
            #     self.model_name = file["key"]
            #     self.model_actual_url = file["links"]["self"]
            #     if self.model_file_extension is None or self.model_name.lower().endswith(self.model_file_extension.lower()):
            #         try:
            #             r = requests.get(self.model_actual_url, stream=True)
            #             r.raise_for_status()

            #             file_path = os.path.join(self.model_save_path, self.model_name)
            #             with open(file_path, "wb") as f:
            #                 for chunk in r.iter_content(chunk_size=8192): # file is downloaded in chunks of 8192 bytes (8kb)
            #                     f.write(chunk)
            #         except requests.exceptions.RequestException as e:
            #             print(f"{e}")
        else:
            self.notify_user("Message", "So far, model to be downloaded needs to be on Zenodo or on Github.")


    def _on_click_select_image_folder(self):
        """Interactively select folder to analyze"""

        self.image_folder = Path(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        self.image_list.update_from_path(self.image_folder)
        self.reset_channels = True

        return self.image_folder
    

    def _on_click_select_model_folder(self):
        """Interactively select folder from models to load from"""

        self.model_folder = Path(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        self.model_list.update_models_from_path(self.model_folder)
        self.reset_channels = True
    

    def _on_slider_change(self, value):
        """Reads the changed value of the expected median diameter slider"""

        self.expected_median_diameter = value
    
    def initialize_model(self):
        """Initializes the Cellpose model with more explicit exception handling"""

        if self.check_use_gpu.isChecked():
            if int(str(version).split(".")[0]) >3:
                try:
                    if core._use_gpu_torch() == True:
                        use_gpu = True
                        #avoid cuda OutOfMemoryError
                        try:
                            _, total = torch.cuda.mem_get_info(torch.device('cuda:0'))
                            total = total/ 1024 ** 2
                            if total < 3000:
                                use_gpu = False
                                if self.supress_notifications == False:
                                    self.notify_user("Not enough CUDA Memory","Not enough GPU RAM for running Cellpose-SAM. Switching to CPU - Processing will be very slow!")
                                    self.check_use_gpu.setChecked(False)
                        except:
                            pass
                    else:
                        if self.supress_notifications == False:
                            self.notify_user("GPU Not Available","Neither TORCH CUDA nor MPS version installed/working.Switching to CPU - Processing will be very slow!")
                        use_gpu = False
                except:
                    pass
            else:
                use_gpu = True  
        else:
            use_gpu = False
        try:
            model_path = self.model_path
            model = models.CellposeModel(gpu=use_gpu, pretrained_model=str(model_path))
        except AttributeError:
            self.notify_user("Selection Required", "No model selected. Please select a model from the model list.")
            return
        except torch.cuda.OutOfMemoryError:
            #GPU memory can still be blocked for a long time, which will crash napari at end of call
            torch.cuda.empty_cache()
            self.notify_user("OutOfMemoryError", "CUDA out of memory. Trying segmentation on CPU.")
            self.check_use_gpu.setChecked(False)
            return
        except:
            self.notify_user("Unexpected Error", "Could not load selected model. Try switching off the GPU option or re-installing the cellpose package.")
            return

        if use_gpu == False:
            if self.supress_notifications == False and int(str(version).split(".")[0]) >3:
                self.notify_user("No GPU","Running Segmentation on CPU - Processing will be very slow!")
        return model

    def _on_click_segment_single_image(self):
        """
        Segments one individual selected image, independent of the image extension (.jpg, .png, .tif, ...).
        """
        # single image:
        try:
            Path(self.image_path)
        except TypeError:
            self.notify_user("No Image Selected","Please select an image from the image list")
            return
        image_path = self.image_path

        model = self.initialize_model()

        MODEL_ID = Path(self.model_name).stem
        img_id = Path(self.image_name).stem
        if self.check_save_mask.isChecked():
            SAVE_MASKS = True
        else:
            SAVE_MASKS = False

        if self.pred_directory.value.as_posix() == "No local path":
            TAR_DIR = ""
        else:
            TAR_DIR = self.pred_directory.value

        self.mask_l, self.flow_l, self.styles_l = predict_single_image(
            image_path=image_path, 
            model=model, diameter=self.expected_median_diameter, mute=True,
            return_results=True, save_masks=SAVE_MASKS,
            tar_dir=TAR_DIR, model_id=MODEL_ID)

        self.viewer.add_labels(self.mask_l[0], name=f"{img_id}_{MODEL_ID}_pred")
        
    
    def notify_user(self, message_title, message):
        """
        Generates a pop up message box an notifies the user with a message.
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(str(message_title))
        msg_box.setText(str(message))
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()


    def _on_click_save_manually_processed_mask(self):
        """Saves the maually processed mask in the folder selected below the button."""

        target_directory = self.man_proc_directory.value
        mask_name = self.viewer.layers.selection.active.name
        mask = self.viewer.layers.selection.active
        try:
            io.imsave(f'{target_directory}/{mask_name}_manual.tif', mask.data)
        except:
            self.notify_user("Selection Required", "Please select a folder to save manually processed mask.")

    
    def _on_click_segment_image_folder(self):
        """
        Segments all images with a selected extension (.jpg, .png, .tif) from a folder.
        Displays original images and their segmentation masks in the napari viewer.
        Masks can be saved in a selected folder.
        """

        model = self.initialize_model()
        
        # single image:
        path_images_in_folder = self.image_folder

        if self.check_save_mask.isChecked():
            SAVE_MASKS = True
        else:
            SAVE_MASKS = False
        MODEL_ID = Path(self.model_name).stem

        if self.pred_directory.value.as_posix() == "No local path":
            TAR_DIR = ""    
        else:
            TAR_DIR = self.pred_directory.value

        if self.radio_segment_jpgs.isChecked():
            self.img_extension = [".jpg",".jpeg"]
        if self.radio_segment_pngs.isChecked():
             self.img_extension = [".png"]
        if self.radio_segment_tiffs.isChecked():
             self.img_extension = [".tif",".tiff"]

        self.img_list = []
        for image_in_folder in os.listdir(path_images_in_folder):
            for img_ext in self.img_extension:
                if image_in_folder.endswith(img_ext):
                    self.img_list.append(image_in_folder)

        if self.check_use_georef.isChecked():
            try: 
                from osgeo import gdal
                gdal.UseExceptions()
            except ModuleNotFoundError:
                if self.supress_notifications == False:
                    self.notify_user("Caution !", "GDAL not installed. Please install GDAL to keep CRS info for GeoTIFF files.")
                pass

        for idx, img in enumerate(self.img_list):
            if ("mask" in img) or ("pred" in img) or ("flow" in img) or ("composite" in img):
                self.notify_user("Caution !", "You have processed images (masks, or predictions or flows or composites) in your image folder!")
                break
            else:
                self.mask_l, self.flow_l, self.styles_l = predict_single_image(
                    image_path=path_images_in_folder.joinpath(img), 
                    model=model,
                    mute=True, 
                    return_results=True,
                    save_masks=SAVE_MASKS,
                    tar_dir=TAR_DIR,
                    model_id=MODEL_ID,
                    diameter=self.expected_median_diameter)
                self.viewer.open(path_images_in_folder.joinpath(img))
                self.viewer.add_labels(self.mask_l, name=f"{Path(img).stem}_{MODEL_ID}_pred")
                self.progress_bar.setValue(int((idx + 1) / len(self.img_list) * 100))

                if self.check_use_georef.isChecked() and (".tif" in self.img_extension or ".tiff" in self.img_extension):
                    try:
                        self.src_tfw = path_images_in_folder.joinpath(f"{Path(img).stem}.tfw")
                        self.tar_tfw = path_images_in_folder.joinpath(f"{Path(img).stem}_{MODEL_ID}_pred.tfw")
                        shutil.copy(self.src_tfw, self.tar_tfw)
                        self.img_georef_path = path_images_in_folder.joinpath(img)
                        self.pred_georef_path = path_images_in_folder.joinpath(f"{Path(img).stem}_{MODEL_ID}_pred.tif")
                        self.dataset_georef = gdal.Open(self.img_georef_path)
                        projection   = self.dataset_georef.GetProjection()
                        geotransform = self.dataset_georef.GetGeoTransform()
                        #update metadata
                        self.dataset_pred_georef = gdal.Open(self.pred_georef_path, gdal.GA_Update)    
                        self.dataset_pred_georef.SetProjection(projection)
                        self.dataset_pred_georef.SetGeoTransform(geotransform)             
                        #close raster files
                        self.dataset_georef = None
                        self.dataset_pred_georef = None 
                    except:
                        if self.supress_notifications == False:
                            self.notify_user("Caution !", "Georeference of tif/tiff files incomplete. Predictions might not be correctly referenced.")
                        pass

        self.progress_bar.setValue(100)  # Ensure it's fully completed


    def _on_select_image(self, current_item, previous_item):
        '''
        Selects one image from an image list and opens it in napari.
        In case that the "Load pred(s)" checkbox is checked,
        the function also loads the corresponding predicted
        masks from the mask folder.
        '''

        success = self.open_image()

        if self.check_load_saved_prediction_mask.isChecked():
            relevant_prediction_path = find_match_in_folder(
                folder=self.pred_directory.value,
                image_name=self.image_name,
                model_str='', data_str='pred', data_format='tif')
            if relevant_prediction_path is None:
                return False
            success = self.viewer.open(relevant_prediction_path, layer_type="labels")

        if not success:
            return False
        else:
            return self.image_path
    

    def _on_select_model(self, current_item, previous_item):
        '''Selects one model from a model list.'''

        # if file list is empty stop here
        if self.model_list.currentItem() is None:
            return False
        
        # extract model path
        self.model_name = self.model_list.currentItem().text()
        self.model_path = self.model_list.folder_path.joinpath(self.model_name)
        
        return self.model_path
        

    def open_image(self):
        '''Opens a selected image in napari.'''

        # clear existing layers.
        while len(self.viewer.layers) > 0:
             self.viewer.layers.clear()

        # if file list is empty stop here
        if self.image_list.currentItem() is None:
            return False
        
        # open image
        self.image_name = self.image_list.currentItem().text()
        self.image_path = self.image_list.folder_path.joinpath(self.image_name)
        self.viewer.open(self.image_path)


    def _on_click_compute_performance_folder(self):
        """
        Compute performance on folder
        """

        imgs,lbls,preds = data_loader.load_from_folders(
            image_directory=self.image_folder,
            label_directory=self.perf_mask_directory.value,
            pred_directory=self.perf_pred_directory.value,
            label_str=self.qtext_mask_str.text(),
            pred_str=self.qtext_pred_str.text()
            )
        evals = eval_set(imgs=imgs, lbls=lbls, preds=preds, save_results=True, tar_dir=self.perf_pred_directory.value)
        # compute mAP
        mAP = 0
        for key, val in evals.items():
            mAP += np.mean(val['ap']) / len(evals)
            self.mAP = mAP
        # plot       
        self.mpl_widget.canvas.figure
        self.axes.clear()
        plotting.AP_IoU_plot(evals, title='', ax=self.axes, fontcolor='white')

        # add mAP
        # Get bounding box of the legend in display coordinates (pixels)
        bbox = self.axes.get_legend().get_window_extent()
        bbox_fig = bbox.transformed(self.axes.transAxes.inverted())
        x_center = bbox_fig.x0 + bbox_fig.width / 2
        y_below = bbox_fig.y0 - 0.02
        self.axes.text(x_center, y_below, f'mAP: {self.mAP:.2f}',
                       fontsize=12, color='black', ha='center', va='top',
                       transform=self.axes.transAxes)
        
        self.mpl_widget.canvas.figure.canvas.draw()
        self.performance_plot_type = 'dataset'

    def _on_click_compute_performance_single_image(self):
        """
        Compute performance on single image
        """
        
        if self.image_list.currentItem() is None:
            raise ValueError("No image selected")
        
        imgs = [self.image_list.folder_path.joinpath(self.image_list.currentItem().text())]
        lbls = data_loader.find_imgs_masks(
            image_path=self.perf_mask_directory.value,
            format='tif',
            filter_str=imgs[0].stem + self.qtext_mask_str.text())
        preds = data_loader.find_imgs_masks(
            image_path=self.perf_pred_directory.value,
            format='tif',
            filter_str=imgs[0].stem + "*" + self.qtext_pred_str.text())

        evals = eval_set(imgs=imgs, lbls=lbls, preds=preds, save_results=False)
        self.mAP = np.mean(evals[0]['ap'])
        self.mpl_widget.canvas.figure
        self.axes.clear()
        plotting.AP_IoU_plot(evals, title='', ax=self.axes, fontcolor='white')#,test_idxs=test_idxs1)
        # fix plot after creation. Ideally a single image plot function should
        # be added to the imagegrains library
        for line in self.axes.lines:
            if line.get_label() in ['Dataset avg.']:
                line.remove()
        for col in self.axes.collections:
            if col.get_label() in ['1 Std. dev.']:
                col.remove()
        
        bbox = self.axes.get_legend().get_window_extent()
        bbox_fig = bbox.transformed(self.axes.transAxes.inverted())
        x_center = bbox_fig.x0 + bbox_fig.width / 2
        y_below = bbox_fig.y0 - 0.02
        self.axes.text(x_center, y_below, f'mAP: {self.mAP:.2f}', 
                       fontsize=12, color='black', ha='center', va='top',
                       transform=self.axes.transAxes)

        self.axes.get_legend().remove()
        self.mpl_widget.canvas.figure.canvas.draw()
        self.performance_plot_type = 'single'

    def _on_save_performance_plot(self):
        """
        Save performance plot
        """

        # set export name
        self.plot_white_black(color='black')
        export_name = ''
        if self.performance_plot_type == 'single':
            export_name = self.image_path.stem
        elif self.performance_plot_type == 'dataset':
            export_name = 'dataset'

        self.mpl_widget.canvas.figure.savefig(self.perf_pred_directory.value / f'performance_plot_{export_name}.png', dpi=300, bbox_inches='tight')
        self.plot_white_black(color='white')
        self.mpl_widget.canvas.figure.canvas.draw()

    def plot_white_black(self, color='white'):

        self.axes.tick_params(axis='both', colors=color)
        self.axes.xaxis.label.set_color(color)
        self.axes.yaxis.label.set_color(color)

    def _on_save_average_precision(self):

        imgs,lbls,preds = data_loader.load_from_folders(
            image_directory=self.image_folder,
            label_directory=self.perf_mask_directory.value,
            pred_directory=self.perf_pred_directory.value,
            label_str=self.qtext_mask_str.text(),
            pred_str=self.qtext_pred_str.text()
            )
        evals = eval_set(imgs=imgs, lbls=lbls, preds=preds, save_results=False)
        avg_l, std_l, std_ul, std_ll = compute_average_ap(evals)
        ap_stats_df = pd.DataFrame(
            {'avg': avg_l,
             'std': std_l,
             'std_ul': std_ul,
             'std_ll': std_ll})
        ap_stats_df.to_csv(self.perf_pred_directory.value /
                           'average_precision.csv', index=False)
    

    def _on_check_toggle_visibility(self):
        '''
        Toggles visibility of the 'Model download' elements. If checkbox is checked, 'Model download' elements are visible, 
        otherwise they are invisible. 
        '''

        if self.check_download_model.isChecked():
            self.model_download_group.toggle_visibility('visible')
        else:
            self.model_download_group.toggle_visibility('invisible')

        
        if self.check_change_diameter.isChecked():
            self.qls_expected_median_diameter.setVisible(True)
        else:
            self.qls_expected_median_diameter.setVisible(False)



class VHGroup():
    """Group box with specific layout.

    Parameters
    ----------
    name: str
        Name of the group box
    orientation: str
        'V' for vertical, 'H' for horizontal, 'G' for grid
    """

    def __init__(self, name, orientation='V'):
        self.gbox = QGroupBox(name)
        if orientation=='V':
            self.glayout = QVBoxLayout()
        elif orientation=='H':
            self.glayout = QHBoxLayout()
        elif orientation=='G':
            self.glayout = QGridLayout()
        else:
            raise Exception(f"Unknown orientation {orientation}") 

        self.gbox.setLayout(self.glayout)


class VHGroupModel():
    """Group box with specific layout.

    Parameters
    ----------
    name: str
        Name of the group box
    orientation: str
        'V' for vertical, 'H' for horizontal, 'G' for grid
    """

    def __init__(self, name, orientation='V'):
        self.gbox = QGroupBox(name)
        self.visibility = 'visible'
        if orientation=='V':
            self.glayout = QVBoxLayout()
        elif orientation=='H':
            self.glayout = QHBoxLayout()
        elif orientation=='G':
            self.glayout = QGridLayout()
        else:
            raise Exception(f"Unknown orientation {orientation}") 

        self.gbox.setLayout(self.glayout)
    

    def toggle_visibility(self, visibility):
        '''Toggles the visibility of all elements bound to the VHGroupModel.'''

        self.visibility = visibility
        if self.visibility == 'invisible':
            self.gbox.setVisible(False)
        else:
            self.gbox.setVisible(True)
