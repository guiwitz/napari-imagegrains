from typing import TYPE_CHECKING
from pathlib import Path
from warnings import warn

from magicgui.widgets import create_widget, Table

from qtpy.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QTabWidget,
                            QLabel, QFileDialog, QLineEdit, QDoubleSpinBox,
                            QCheckBox, QMessageBox, QAbstractItemView)
import pandas as pd
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
from napari_matplotlib.base import NapariMPLWidget

from .imgr_proc_widget import VHGroup
from .folder_list_widget import FolderList
from .utils import (find_match_in_folder, find_matching_data_index,
                    read_complete_grain_files)
from imagegrains import grainsizing, data_loader, plotting
from imagegrains.grainsizing import scale_grains

if TYPE_CHECKING:
    import napari


class ImageGrainStatsWidget(QWidget):
    """Widget for grain size analysis"""

    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        
        self.viewer = viewer
        
        # name of current image
        self.image_name = None
        # df for current image
        self.props_df_image = None
        # df for all images
        self.props_df_dataset = None
        # list of skimage.measure._regionprops.RegionProperties for current image
        self.props_image = None
        # list of list of skimage.measure._regionprops.RegionProperties for all images
        self.props_dataset = None
        self.file_ids = None
        # displayble table
        self.results_table = Table()

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # properties tab
        self.properties = QWidget()
        self._properties_layout = QVBoxLayout()
        self.properties.setLayout(self._properties_layout)
        self.tabs.addTab(self.properties, 'Properties')


        ### Elements "Image selection"
        self.image_group = VHGroup('Image selection', orientation='G')
        self._properties_layout.addWidget(self.image_group.gbox)
        
        self.btn_select_image_folder = QPushButton("Select image folder")
        self.btn_select_image_folder.setToolTip("Select image Folder")
        self.image_group.glayout.addWidget(self.btn_select_image_folder, 0, 0, 1, 1)

        ##### Elements "Image list" #####
        self.image_list = FolderList(viewer, file_extensions=['.png', '.jpg', '.jpeg', '.tif', '.tiff'])
        self.image_list.setMaximumHeight(100)
        self.image_group.glayout.addWidget(self.image_list, 1, 0, 1, 1)

        self.btn_select_mask_folder = QPushButton("Select predictions folder")
        self.btn_select_mask_folder.setToolTip("Select predictions Folder")
        self.image_group.glayout.addWidget(self.btn_select_mask_folder, 0, 1, 1, 1)

        ##### Elements "Mask list" #####
        self.mask_list = FolderList(viewer, file_extensions=['.tif', '.tiff'])
        self.mask_list.setMaximumHeight(100)
        self.mask_list.setSelectionMode(QAbstractItemView.NoSelection)

        self.image_group.glayout.addWidget(self.mask_list, 1, 1, 1, 1)

        self.image_group.gbox.setMaximumHeight(self.image_group.gbox.sizeHint().height())

        #### mask options
        self.mask_group = VHGroup('Prediction selection', orientation='G')
        self._properties_layout.addWidget(self.mask_group.gbox)
        self.qtext_mask_str = QLineEdit("_pred")
        self.mask_group.glayout.addWidget(QLabel("Prediction string"), 0, 0, 1, 1)
        self.mask_group.glayout.addWidget(self.qtext_mask_str, 0, 1, 1, 1)

        self.qtext_model_str = QLineEdit("")
        self.mask_group.glayout.addWidget(QLabel("Model string"), 1, 0, 1, 1)
        self.mask_group.glayout.addWidget(self.qtext_model_str, 1, 1, 1, 1)

        self.mask_group.gbox.setMaximumHeight(self.mask_group.gbox.sizeHint().height())
        
        ### Elements "Analysis"
        self.analysis_group = VHGroup('Analysis', orientation='G')
        self._properties_layout.addWidget(self.analysis_group.gbox)

        self.btn_run_grainsize_on_folder = QPushButton("Run on folder")
        self.btn_run_grainsize_on_folder.setToolTip("Run grain measure on folder")
        self.analysis_group.glayout.addWidget(self.btn_run_grainsize_on_folder, 0, 0, 1, 1)

        self.btn_run_grainsize_on_image = QPushButton("Run on image")
        self.btn_run_grainsize_on_image.setToolTip("Run grain measure on image")
        self.analysis_group.glayout.addWidget(self.btn_run_grainsize_on_image, 1, 0, 1, 1)

        # load grain sizes for folder
        self.btn_load_grainsize = QPushButton("Load for folder")
        self.btn_load_grainsize.setToolTip("Load for folder")
        self.analysis_group.glayout.addWidget(self.btn_load_grainsize, 2, 0, 1, 1)
        
        '''# load grain sizes for image
        self.btn_load_grainsize_image = QPushButton("Load for image")
        self.btn_load_grainsize_image.setToolTip("Load for image")
        self.analysis_group.glayout.addWidget(self.btn_load_grainsize_image, 3, 0, 1, 1)'''

        self.mpl_widget = NapariMPLWidget(viewer)
        self.axes = self.mpl_widget.canvas.figure.subplots()
        self.analysis_group.glayout.addWidget(self.mpl_widget.canvas, 0, 1, 4, 1)
        self.analysis_group.glayout.addWidget(self.mpl_widget.toolbar, 4, 1, 1, 2)

        self.combobox_prop_to_plot = create_widget(value = 'area', 
                                                 options={'choices': ['area']},
                                                widget_type='ComboBox')
        self.analysis_group.glayout.addWidget(self.combobox_prop_to_plot.native, 4, 0, 1, 1)

        self.check_scale = QCheckBox("Scale")
        self.check_scale.setToolTip("Scale image")
        self.check_scale.setChecked(False)
        self.analysis_group.glayout.addWidget(self.check_scale, 5, 0, 1, 1)

        self.spinbox_scale = QDoubleSpinBox()
        self.spinbox_scale.setToolTip("Indicate conversion factor from pixel to mm")
        self.spinbox_scale.setDecimals(4)
        self.spinbox_scale.setRange(0.0, 1000)
        self.spinbox_scale.setSingleStep(0.0001)
        self.spinbox_scale.setValue(1)
        self.spinbox_scale.setSuffix(" px/mm")
        self.spinbox_scale.setEnabled(False)
        self.analysis_group.glayout.addWidget(self.spinbox_scale, 5, 1, 1, 1)

        ### Elements "Display fit"
        self.displayfit_group = VHGroup('Display fit', orientation='G')
        self._properties_layout.addWidget(self.displayfit_group.gbox)

        self.dropdown_fit_method = create_widget(value = 'ellipse', 
                                                 options={'choices': ['ellipse', 'mask_outline']},
                                                widget_type='ComboBox')
        self.displayfit_group.glayout.addWidget(self.dropdown_fit_method.native)
        self.btn_display_fit = QPushButton("Display fit")
        self.btn_display_fit.setToolTip("Display fit")
        self.displayfit_group.glayout.addWidget(self.btn_display_fit)
        self.displayfit_group.gbox.setMaximumHeight(self.displayfit_group.gbox.sizeHint().height())


        # Grain size tab
        self.grainsize = QWidget()
        self._grainsize_layout = QVBoxLayout()
        self.grainsize.setLayout(self._grainsize_layout)
        self.tabs.addTab(self.grainsize, 'Grain size')

        ### Elements "Image selection"
        self.grainsize_plot_group = VHGroup('Plot', orientation='G')
        self._grainsize_layout.addWidget(self.grainsize_plot_group.gbox)

        self.grainsize_plot = NapariMPLWidget(viewer)
        self.grainsize_axes = self.grainsize_plot.canvas.figure.subplots()
        self.grainsize_plot_group.glayout.addWidget(self.grainsize_plot.canvas)
        self.grainsize_plot_group.glayout.addWidget(self.grainsize_plot.toolbar)

        self.combobox_props_for_size = create_widget(value = 'ell: b-axis (px)',
                                                 options={'choices': ['ell: b-axis (px)', 'ell: a-axis (px)']},
                                                widget_type='ComboBox')
        self.grainsize_plot_group.glayout.addWidget(self.combobox_props_for_size.native)

        self.btn_plot_dataset = QPushButton("Plot for folder")
        self.btn_plot_dataset.setToolTip("Plot for folder")
        self.grainsize_plot_group.glayout.addWidget(self.btn_plot_dataset)

        self.btn_plot_single_image = QPushButton("Plot for image")
        self.btn_plot_single_image.setToolTip("Plot for image")
        self.grainsize_plot_group.glayout.addWidget(self.btn_plot_single_image)

        self.uncertainty_group = VHGroup('Uncertainty', orientation='G')
        self._grainsize_layout.addWidget(self.uncertainty_group.gbox)
        self.check_uncertainty = QCheckBox("Plot uncertainty")
        self.check_uncertainty.setToolTip("Plot uncertainty")
        self.check_uncertainty.setChecked(False)
        self.uncertainty_group.glayout.addWidget(self.check_uncertainty, 0, 0, 1, 1)

        self.combobox_uncertainty = create_widget(value = 'bootstrapping',
                                                 options={'choices': ['bootstrapping', 'Simple MC']},
                                                widget_type='ComboBox')
        self.combobox_uncertainty.hide()
        #self.check_uncertainty.changed.connect(self.combobox_uncertainty.show)
        self.uncertainty_group.glayout.addWidget(self.combobox_uncertainty.native, 0, 1, 1, 1)
        

        self.add_connections()

    def add_connections(self):

        self.image_list.currentItemChanged.connect(self._on_select_image)
        self.btn_select_mask_folder.clicked.connect(self._on_select_mask_folder)
        self.btn_select_image_folder.clicked.connect(self._on_select_image_folder)
        self.btn_run_grainsize_on_folder.clicked.connect(self._on_run_grainsize_on_folder)
        self.btn_run_grainsize_on_image.clicked.connect(self._on_run_grainsize_on_image)
        self.check_scale.toggled.connect(self.spinbox_scale.setEnabled)
        self.btn_display_fit.clicked.connect(self._on_display_fit)
        self.btn_plot_dataset.clicked.connect(self._on_plot_gsd_dataset)
        self.btn_plot_single_image.clicked.connect(self._on_plot_gsd_image)
        self.combobox_prop_to_plot.changed.connect(self._on_select_prop_to_plot)
        self.check_uncertainty.toggled.connect(self.combobox_uncertainty.native.setVisible)

        self.btn_load_grainsize.clicked.connect(self._on_load_grainsize_dataset)
        #self.btn_load_grainsize_image.clicked.connect(self._on_load_grainsize_image)

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

    def _on_select_image_folder(self):
        """Interactively select folder to analyze"""

        self.image_folder = Path(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        self.image_list.update_from_path(self.image_folder)
        self.reset_channels = True

        return self.image_folder
    
    def _on_select_mask_folder(self):
        """Interactively select folder to analyze"""

        self.mask_folder = Path(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        self.mask_list.update_from_path(self.mask_folder)
        self.reset_channels = True

        self.reset_props()

    def reset_props(self):

        # reset properties
        self.props_df_image = None
        self.props_df_dataset = None
        self.props_image = None
        self.props_dataset = None
        self.file_ids = None
        self.results_table.clear()

        return self.mask_folder

    def _on_run_grainsize_on_folder(self):
        
        self.plot_type = 'multi'
        composite_name = self.qtext_model_str.text() + self.qtext_mask_str.text()
        self.props_df_dataset, self.props_dataset, self.file_ids = grainsizing.grains_in_dataset(
            data_dir=self.mask_folder, 
            mask_str=composite_name,
            tar_dir=self.mask_folder,
            return_results=True)
        
        if self.check_scale.isChecked():
            for ind in range(len(self.props_df_dataset)):
                scale = self.spinbox_scale.value()
                self.props_df_dataset[ind] = scale_grains(
                    self.props_df_dataset[ind], resolution=scale, 
                    tar_dir=self.mask_folder, gsd_path=self.file_ids[ind]+'_grains',
                    return_results=True)
        
        for ind, x in enumerate(self.props_df_dataset):
            x['file_id'] = self.file_ids[ind]
        self.props_df_dataset = pd.concat(self.props_df_dataset)
        
        self._update_combobox_props(self.props_df_dataset.drop(columns='file_id').columns)
        self._update_combobox_props_for_size(self.props_df_dataset.drop(columns='file_id').columns)
        self._on_select_prop_to_plot()

    def _on_run_grainsize_on_image(self, event=None):

        self.plot_type = 'single'
        self.props_df_image, self.props_image = grainsizing.grains_from_masks(
            masks=self.mask_layer.data)
        
        if self.check_scale.isChecked():
            self.props_df_image = scale_grains(
                    self.props_df_image, resolution=self.spinbox_scale.value(),
                    file_id='rescaled', save_gsds=False, return_results=True)
                
        self._update_combobox_props(self.props_df_image.columns)
        self._update_combobox_props_for_size(self.props_df_image.columns)
        self._on_select_prop_to_plot()

        self.mask_layer.properties = self.props_df_image
        self.create_table_widget(self.props_df_image)

    def _add_scaled_columns(self):
        
        if self.check_scale.isChecked():
            scale = self.spinbox_scale.value()
            for col in ['area', 'ell: b-axis (px)', 'ell: a-axis (px)']:
                if self.props_df_image is not None:
                    self.props_df_image[col.replace('px', 'mm')] = scale * self.props_df_image[col]
                if self.props_df_dataset is not None:
                    self.props_df_dataset[col.replace('px', 'mm')] = scale * self.props_df_dataset[col]

    def create_table_widget(self, dataframe):
        if self.results_table is None: 
            self.results_table = Table(
                value=dataframe, name="Properties Table"
            )
        else:
            self.results_table.clear()
            self.results_table.set_value(dataframe)
        self.results_table.native.clicked.connect(self.clicked_table)
        self.results_table.read_only = True
        self.results_table.show()

    def clicked_table(self, event=None):
        if "label" in self.results_table.column_headers:
            row = self.results_table.native.currentRow()
            label = int(self.results_table["label"][row])
            self.mask_layer.selected_label = label
        
        
    def _update_combobox_props(self, newprops):
        self.combobox_prop_to_plot.changed.disconnect(self._on_select_prop_to_plot)
        self.combobox_prop_to_plot.choices = newprops
        self.combobox_prop_to_plot.changed.connect(self._on_select_prop_to_plot)

    def _update_combobox_props_for_size(self, newprops):
        self.combobox_props_for_size.changed.disconnect(self._on_select_prop_to_plot)
        self.combobox_props_for_size.choices = newprops
        self.combobox_props_for_size.changed.connect(self._on_select_prop_to_plot)

    def get_grain_files(self):
        """Find the appropriate grain files given: 1. mask and model string, 2. a folder
        containing the grain files, 3. the information whether the grain files are scaled or not."""

        composite_name = self.qtext_model_str.text() + self.qtext_mask_str.text() + '_grains'
        grain_files = data_loader.load_grain_set(file_dir=self.mask_folder, gsd_str=composite_name)
        if self.check_scale.isChecked():
            grain_files = [x for x in grain_files if 're_scaled' in Path(x).stem]
        else:
            grain_files = [x for x in grain_files if 're_scaled' not in Path(x).stem]

        return grain_files

    def _on_load_grainsize_dataset(self, event=None):
        
        self.plot_type = 'multi'
        self.grain_files = self.get_grain_files()
        
        self.props_df_dataset = read_complete_grain_files(grain_file_list=self.grain_files)
        
        for ind, x in enumerate(self.props_df_dataset):
            x['file_id'] = Path(self.grain_files[ind]).stem
        self.props_df_dataset = pd.concat(self.props_df_dataset)
        if 'Unnamed: 0' in self.props_df_dataset.columns:
            self.props_df_dataset.drop(columns='Unnamed: 0', inplace=True)
        
        self._update_combobox_props(self.props_df_dataset.drop(columns='file_id').columns)
        self._update_combobox_props_for_size(self.props_df_dataset.drop(columns='file_id').columns)
        self._on_select_prop_to_plot()

    def _on_load_grainsize_image(self, event=None):
        
        self.plot_type = 'single'
        composite_name = self.qtext_model_str.text() + self.qtext_mask_str.text() + '_grains'
        grain_files = data_loader.load_grain_set(file_dir=self.mask_folder, gsd_str=composite_name)
        grain_files = [x for x in grain_files if Path(self.image_name).stem in x]
        if self.check_scale.isChecked():
            self.grain_files = [x for x in self.grain_files if 're_scaled' in Path(x).stem]
        else:
            self.grain_files = [x for x in self.grain_files if 're_scaled' not in Path(x).stem]
        
        if len(grain_files) == 0:
            raise ValueError(f'No grain file found for image {self.image_name}')
        elif len(grain_files) > 1:
            raise ValueError(f'Multiple grain files found for image {self.image_name}')
        
        self.props_df_image = read_complete_grain_files(grain_file_list=grain_files)[0]
        self.mask_layer.properties = self.props_df_image
        self.create_table_widget(self.props_df_image)

        # concatenated dataframe of all images
        self._update_combobox_props(self.props_df_image.columns)
        self._update_combobox_props_for_size(self.props_df_image.columns)
        self._on_select_prop_to_plot()


    def _on_select_prop_to_plot(self, event=None):

        self.axes.clear()
        if self.plot_type == 'multi':
            sns.histplot(data=self.props_df_dataset, x=self.combobox_prop_to_plot.value, ax=self.axes)
        else:
            sns.histplot(data=self.props_df_image, x=self.combobox_prop_to_plot.value, ax=self.axes)
        
        self.axes.tick_params(axis='both', colors='white')
        self.axes.xaxis.label.set_color('white')
        self.axes.yaxis.label.set_color('white')
        self.mpl_widget.canvas.figure.canvas.draw()

    def _on_select_prop_for_size(self, event=None):

        self._on_plot_gsd_dataset()

    def _on_select_image(self, current_item, previous_item):

        success = self.open_image()
        if not success:
            return False
        else:
            self.results_table.clear()
            self.axes.clear()
            if self.props_df_dataset is not None:
                ref_files = self.props_df_dataset['file_id'].unique()
                index = find_matching_data_index(self.image_path, ref_files)
                self.props_df_image = self.props_df_dataset[self.props_df_dataset['file_id'] == ref_files[index[0]]]
                self.create_table_widget(self.props_df_image)

            # find mask corresponding to image
            self.mask_path = None
            self.mask_path = find_match_in_folder(
                self.mask_folder, 
                self.image_name, 
                model_str=self.qtext_model_str.text(),
                data_str=self.qtext_mask_str.text(),
                data_format='tif')
            self.open_mask()

            return self.image_path
        
    def open_image(self):

        # clear existing layers.
        while len(self.viewer.layers) > 0:
             self.viewer.layers.clear()

        # if file list is empty stop here
        if self.image_list.currentItem() is None:
            return False
        
        # open image
        self.image_name = self.image_list.currentItem().text()
        self.image_path = self.image_list.folder_path.joinpath(self.image_name)

        self.props_df_image = None
        self.props_image = None

        self.viewer.open(self.image_path)
        return True

    def open_mask(self):

        if self.mask_path is None:
            return False
        self.mask_layer = self.viewer.open(self.mask_path, layer_type='labels')[0]


    def _on_display_fit(self):
        
        # check that information is available. props can be available from the full dataset (props_dataset)
        # or from the image (props_image)
        if self.props_dataset is None:
            if self.props_image is None:
                self._on_run_grainsize_on_image()
            current_props = self.props_image
        else:
            model_str = self.qtext_model_str.text() if self.qtext_model_str.text() != "" else None
            match_index = find_matching_data_index(self.image_path, self.file_ids, key_string=model_str)
            if len(match_index) == 0:
                raise ValueError(f'No mask found for current image {self.image_path}')
            elif len(match_index) > 1:
                raise ValueError(f'Multiple masks {match_index} found for current image {self.image_path}')
            else:
                current_props = self.props_dataset[match_index[0]]

        if self.dropdown_fit_method.value == 'mask_outline':
            padding_size = 2
            ## temporary fix as the padding function only handles the cases of 'mask_outline' and 'convex_hull'
            #_,_,a_coords,b_coords = grainsizing.fit_grain_axes(current_props, method=self.dropdown_fit_method.value,padding_size=padding_size)
            _,_,a_coords,b_coords = grainsizing.fit_grain_axes(current_props, method='mask_outline',padding_size=padding_size)

        if 'contours' in self.viewer.layers:
            self.viewer.layers['contours'].data = []#clear()
        else:
            self.viewer.add_shapes(name='contours', face_color=[0,0,0,0], edge_color='orange')
        
        if 'axis' in self.viewer.layers:
            self.viewer.layers['axis'].data = []#clear()
        else:
            self.viewer.add_shapes(name='axis', face_color=[0,0,0,0], edge_color='red')

        for _idx in range(len(current_props)):

            if self.dropdown_fit_method.value == 'mask_outline':

                miny, minx, maxy, maxx = current_props[_idx].bbox

                img_pad = grainsizing.image_padding(current_props[_idx].image,padding_size=padding_size)
                contours = grainsizing.contour_grain(img_pad)
                for contour in contours:
                    self.viewer.layers['contours'].add_polygons([np.array(contour) + np.array([-(padding_size-.5)+miny, -(padding_size-.5)+minx])])
                    self.viewer.layers['axis'].add_lines([np.array(a_coords[_idx]) + np.array([-(padding_size-.5)+miny, -(padding_size-.5)+minx])], edge_color='red')
                    self.viewer.layers['axis'].add_lines([np.array(b_coords[_idx]) + np.array([-(padding_size-.5)+miny, -(padding_size-.5)+minx])], edge_color='blue')
            
            elif self.dropdown_fit_method.value == 'ellipse':
                x0,x1,x2,x3,x4,y0,y1,y2,y3,y4,x,y= plotting.ell_from_props(current_props,_idx)
                self.viewer.layers['axis'].add_polygons(np.array([y,x]).T, edge_color='orange')
                self.viewer.layers['axis'].add_lines(np.array([[y1, x1],[y4, x4]]), edge_color='blue')
                self.viewer.layers['axis'].add_lines(np.array([[y2, x2],[y3, x3]]), edge_color='red')

    def _on_plot_gsd_dataset(self):

        column = self.combobox_props_for_size.value
        self.grain_files = self.get_grain_files()
        if len(self.grain_files) == 0:
            #warn(f'No grain files found for {self.mask_folder.name}. Please run the grain size analysis for the full folder first.')
            self.notify_user("Analysis required", "No grain files found. Please run the grain size analysis for the full folder first in the Properties tab.")
            return
        gsd_l, id_l = grainsizing.gsd_for_set(gsds=self.grain_files, column=column)

        self.grainsize_axes.clear()
        colors = plt.cm.tab10(np.linspace(0, 1, len(gsd_l)))
        for gsd, id, c in zip(gsd_l, id_l, colors):
            plotting.plot_gsd(gsd=gsd, ax=self.grainsize_axes, gsd_id=id,
                              color=c, label_axes=True, length_max=np.max(gsd_l))
        
        self.grainsize_axes.set_title(f'Grain size distribution for {self.mask_folder.name}', fontsize=12, color='white')
        self.grainsize_axes.set_xlabel(f'Grain size {column}', fontsize=10, color='white')
        self.grainsize_axes.tick_params(axis='both', colors='white')
        self.grainsize_axes.xaxis.label.set_color('white')
        self.grainsize_axes.yaxis.label.set_color('white')
        self.grainsize_axes.legend()
        self.grainsize_plot.canvas.figure.canvas.draw()

    def _on_plot_gsd_image(self):

        if self.image_name is None:
            self.notify_user("Image required", "No image selected. Please select an image first.")
            return
        
        column = self.combobox_props_for_size.value
        self.grain_files = self.get_grain_files()
        self.grain_files = [x for x in self.grain_files if Path(self.image_name).stem in x]
        gsd_l, id_l = grainsizing.gsd_for_set(gsds=self.grain_files, column=column)

        idx = 0

        self.grainsize_axes.clear()
        plotting.plot_gsd(gsd=gsd_l[idx], ax=self.grainsize_axes,
                          label_axes=True, length_max=np.max(gsd_l[idx]))
        self.grainsize_axes.set_title(f'Grain size distribution for {id_l[idx]}', fontsize=12, color='white')
        self.grainsize_axes.set_xlabel(f'Grain size {column}', fontsize=10, color='white')
        self.grainsize_axes.tick_params(axis='both', colors='white')
        self.grainsize_axes.xaxis.label.set_color('white')
        self.grainsize_axes.yaxis.label.set_color('white')

        if self.check_uncertainty.isChecked():
            from imagegrains import gsd_uncertainty 
            num_it = 1000
            column_name = self.combobox_props_for_size.value

            # Percentile uncertainty with bootstrapping (counting statistics only)
            res_dict_bs = gsd_uncertainty.dataset_uncertainty(
                gsds=self.grain_files,
                num_it=num_it,
                mute=True,
                column_name=column_name,
                return_results=True,
                sep=',',
                method = self.combobox_uncertainty.value,
                tar_dir= self.mask_folder)
            
            plotting.plot_gsd_uncert(res_dict_bs['0'],color='k', ax=self.grainsize_axes)

        self.grainsize_plot.canvas.figure.canvas.draw()