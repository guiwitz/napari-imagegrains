import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


from typing import TYPE_CHECKING
from pathlib import Path

from qtpy.QtWidgets import QVBoxLayout, QTabWidget, QPushButton, QWidget, QFileDialog,  QLineEdit, QGroupBox, QHBoxLayout, QGridLayout, QLabel, QCheckBox, QProgressBar, QRadioButton, QMessageBox

from imagegrains.segmentation_helper import eval_set
from imagegrains import data_loader, plotting

from cellpose import models, io
from napari_matplotlib.base import NapariMPLWidget

from magicgui.widgets import create_widget


import warnings
#warnings.filterwarnings("ignore")

import requests

from .folder_list_widget import FolderList
from .access_single_image_widget import predict_single_image

if TYPE_CHECKING:
    import napari


class ImageGrainProcWidget(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer

        self.image_path = None

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

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
        self.lbl_select_model_for_download = QLabel("Model URL (Github or Zenodo)")
        self.repo_model_path_display = QLineEdit("No URL")
        self.lbl_select_directory_for_download = QLabel("Download model to directory")
        # self.local_directory_model_path_display = QLineEdit("No local path")
        self.local_directory_model_path_display = create_widget(value=Path("No local path"), options={"mode": "d", "label": "Choose a directory"})
        self.btn_download_model = QPushButton("Download model")
        self.btn_download_model.setToolTip("Add URL to model repo and click to download models")

        self.model_download_group.glayout.addWidget(self.lbl_select_model_for_download, 0, 0, 1, 1)
        self.model_download_group.glayout.addWidget(self.repo_model_path_display,  0, 1, 1, 1)
        self.model_download_group.glayout.addWidget(self.lbl_select_directory_for_download, 1, 0, 1, 1)
        # self.model_download_group.glayout.addWidget(self.local_directory_model_path_display,  1, 1, 1, 1)
        self.model_download_group.glayout.addWidget(self.local_directory_model_path_display.native,  1, 1, 1, 1)
        self.model_download_group.glayout.addWidget(self.btn_download_model, 2, 0, 1, 2)


        ### Elements "Model selection" ###
        self.model_selection_group = VHGroup('Model selection', orientation='G')
        self._segmentation_layout.addWidget(self.model_selection_group.gbox)

        ##### Elements "Select model folder" #####
        self.btn_select_model_folder = QPushButton("Select model folder")
        self.model_selection_group.glayout.addWidget(self.btn_select_model_folder, 0, 0, 1, 2)

        ##### Elements "Model list" #####
        self.model_list = FolderList(viewer, file_extensions=['.170223'])
        self.model_selection_group.glayout.addWidget(self.model_list, 1, 0, 1, 2)


        ### Elements "Image selection"
        self.image_group = VHGroup('Image selection', orientation='G')
        self._segmentation_layout.addWidget(self.image_group.gbox)
        self.btn_select_image_folder = QPushButton("Select image folder")
        self.btn_select_image_folder.setToolTip("Select Image Folder")
        self.image_group.glayout.addWidget(self.btn_select_image_folder)

        ##### Elements "Image list" #####
        self.image_list = FolderList(viewer, file_extensions=['.png', '.jpg', '.tif'])
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
        self.check_save_mask = QCheckBox('Save pred(s)')
        self.segmentation_option_group.glayout.addWidget(self.check_save_mask, 1, 1, 1, 1)
        self.check_load_saved_prediction_mask = QCheckBox('Load pred(s)')
        self.segmentation_option_group.glayout.addWidget(self.check_load_saved_prediction_mask, 2, 1, 1, 1)
        self.pred_directory = create_widget(value=Path("No local path"), options={"mode": "d", "label": "Choose a directory"})
        self.segmentation_option_group.glayout.addWidget(QLabel("Save preds to"), 3, 0, 1, 1)
        self.segmentation_option_group.glayout.addWidget(self.pred_directory.native, 3, 1, 1, 1)


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
        self.perf_folder_group.glayout.addWidget(QLabel("Pick pred folder"), 0, 0, 1, 1)
        self.perf_folder_group.glayout.addWidget(self.perf_pred_directory.native, 0, 1, 1, 1)
        self.perf_folder_group.glayout.addWidget(QLabel("Pick mask folder"), 1, 0, 1, 1)
        self.perf_folder_group.glayout.addWidget(self.perf_mask_directory.native, 1, 1, 1, 1)
        self.perf_folder_group.gbox.setMaximumHeight(self.perf_folder_group.gbox.sizeHint().height())


        ### Plotting
        self.mpl_widget = NapariMPLWidget(viewer)
        self.axes = self.mpl_widget.canvas.figure.subplots()
        self._options_tab_layout.addWidget(self.mpl_widget.canvas)
        self.btn_compute_performance_single_image = QPushButton("Compute performance single image")
        self._options_tab_layout.addWidget(self.btn_compute_performance_single_image)
        self.btn_compute_performance_folder = QPushButton("Compute performance folder")
        self._options_tab_layout.addWidget(self.btn_compute_performance_folder)

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
    
    def _on_click_download_model(self):
        """Downloads models from Github"""

        if self.repo_model_path_display.text() == "No URL":
            return False
        #if self.local_directory_model_path_display.text() == "No local path":
        if self.local_directory_model_path_display.value == "No local path":
             return False 
        
        self.model_url_user = self.repo_model_path_display.text()
        if "github.com" in self.model_url_user:
            self.model_url_processed = self.model_url_user.replace("github.com", "raw.githubusercontent.com").replace("blob/", "")
            self.model_name = (self.model_url_processed.split("/")[-1])
            # self.model_save_path = self.local_directory_model_path_display.text()
            self.model_save_path = self.local_directory_model_path_display.value

            content_in_bytes = requests.get(str(self.model_url_processed)).content
            assert type(content_in_bytes) is bytes
            with open(str(Path(self.model_save_path).joinpath(self.model_name)), 'wb') as f_out:
                f_out.write(content_in_bytes)
        else:
            self.notify_user("Message", "So far, model to be downloaded needs to be on Github.")


    def _on_click_select_image_folder(self):
        """Interactively select folder to analyze"""

        self.image_folder = Path(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        self.image_list.update_from_path(self.image_folder)
        self.reset_channels = True

        return self.image_folder
    

    def _on_click_select_model_folder(self):
        """Interactively select folder to analyze"""

        model_folder = Path(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        self.model_list.update_from_path(model_folder)
        self.reset_channels = True
    

    def _on_click_segment_single_image(self):
        """
        Segments one individual selected image, independent of the image extension (.jpg, .png, .tif, ...).
        """

        try:
            model_path = self.model_path
            model = models.CellposeModel(gpu=False, pretrained_model=str(model_path))
        except:
            self.notify_user("Selection Required", "No model selected. Please select a model from the model list.")

        # single image:
        if self.image_path is None:
            raise ValueError("No image selected")
        image_path = self.image_path

        if self.pred_directory.value.as_posix() == "No local path":
            SAVE_MASKS = False
            TAR_DIR = ""
            img_id = Path(self.image_name).stem
            MODEL_ID = Path(self.model_name).stem
        else:
            if not self.check_save_mask.isChecked():
                SAVE_MASKS = False
                TAR_DIR = ""
                img_id = Path(self.image_name).stem
                MODEL_ID = Path(self.model_name).stem
            else:
                SAVE_MASKS = True
                TAR_DIR = self.pred_directory.value
                img_id = Path(self.image_name).stem
                MODEL_ID = Path(self.model_name).stem

        self.mask_l, self.flow_l, self.styles_l, self.id_list, self.img_l = predict_single_image(image_path, model, mute=True, return_results=True, save_masks=SAVE_MASKS, tar_dir=TAR_DIR, model_id=MODEL_ID)

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
        GPU usage option not yet implemented.
        """

        try:
            model_path = self.model_path
            model = models.CellposeModel(gpu=False, pretrained_model=str(model_path))
        except:
            self.notify_user("Selection Required", "No model selected. Please select a model from the model list.")

        # single image:
        path_images_in_folder = self.image_folder

        if self.pred_directory.value.as_posix() == "No local path":
            SAVE_MASKS = False
            TAR_DIR = ""
            MODEL_ID = Path(self.model_name).stem
        else:
            if not self.check_save_mask.isChecked():
                SAVE_MASKS = False
                TAR_DIR = ""
                MODEL_ID = Path(self.model_name).stem
            else:
                SAVE_MASKS = True
                TAR_DIR = self.pred_directory.value
                MODEL_ID = Path(self.model_name).stem

        if self.radio_segment_jpgs.isChecked():
            self.img_extension = ".jpg"
        if self.radio_segment_pngs.isChecked():
             self.img_extension = ".png"
        if self.radio_segment_tiffs.isChecked():
             self.img_extension = ".tif"

        img_list = [x for x in os.listdir(path_images_in_folder) if x.endswith(self.img_extension)]

        for idx, img in enumerate(img_list):
            self.mask_l, self.flow_l, self.styles_l, self.id_list, self.img_l = predict_single_image(path_images_in_folder.joinpath(img), model, mute=True, return_results=True, save_masks=SAVE_MASKS, tar_dir=TAR_DIR, model_id=MODEL_ID)
            self.viewer.open(path_images_in_folder.joinpath(img))
            self.viewer.add_labels(self.mask_l, name=f"{img[:-4]}_{MODEL_ID}_pred")
            self.progress_bar.setValue(int((idx + 1) / len(img_list) * 100))

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
            for idx, predicted_mask in enumerate(os.listdir(self.pred_directory.value)):
                if predicted_mask.find(self.image_name[0:-4]) != -1:
                    relevant_predicted_mask = os.listdir(self.pred_directory.value)[idx]
                    relevant_prediction_path = self.pred_directory.value.joinpath(relevant_predicted_mask)
                    self.viewer.open(relevant_prediction_path, layer_type="labels")

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
        evals = eval_set(imgs=imgs, lbls=lbls, preds=preds, save_results=False)
        self.mpl_widget.canvas.figure
        self.axes.clear()
        plotting.AP_IoU_plot(evals,title='FH+', ax=self.axes, fontcolor='white')#,test_idxs=test_idxs1)
        self.mpl_widget.canvas.figure.canvas.draw()


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
        self.mpl_widget.canvas.figure
        self.axes.clear()
        plotting.AP_IoU_plot(evals,title='Performance', ax=self.axes, fontcolor='white')#,test_idxs=test_idxs1)
        # fix plot after creation. Ideally a single image plot function should
        # be added to the imagegrains library
        for line in self.axes.lines:
            if line.get_label() in ['Dataset avg.']:
                line.remove()
        for col in self.axes.collections:
            if col.get_label() in ['1 Std. dev.']:
                col.remove()
        self.axes.get_legend().remove()
        self.mpl_widget.canvas.figure.canvas.draw()
    

    def _on_check_toggle_visibility(self):
        '''
        Toggles visibility of the 'Model download' elements. If checkbox is checked, 'Model download' elements are visible, 
        otherwise they are invisible. 
        '''

        if self.check_download_model.isChecked():
            self.model_download_group.toggle_visibility('visible')
        else:
            self.model_download_group.toggle_visibility('invisible')


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
