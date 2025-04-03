from typing import TYPE_CHECKING
from pathlib import Path
import matplotlib.pyplot as plt

from magicgui.widgets import create_widget
from qtpy.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QTabWidget,
                            QLabel, QFileDialog, QLineEdit, QSizePolicy)
import pandas as pd
import seaborn as sns
import numpy as np
from napari_matplotlib.base import NapariMPLWidget

from .imgr_proc_widget import VHGroup
from .folder_list_widget import FolderList
from .utils import find_match_in_folder, find_matching_data_index, read_complete_grain_files
from imagegrains import grainsizing, data_loader, plotting

if TYPE_CHECKING:
    import napari


class ImageGrainStatsWidget(QWidget):
    """Widget for grain size analysis"""

    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        
        self.viewer = viewer
        #self.setLayout(QVBoxLayout())

        # df for current image
        self.props_df_image = None
        # list of df per image
        self.props_df_dataset = None
        # concatenated dataframe of all images
        self.df_props = None
        # list of skimage.measure._regionprops.RegionProperties for current image
        self.props_image = None
        # list of list of skimage.measure._regionprops.RegionProperties for all images
        self.props_dataset = None
        self.file_ids = None

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
        self.image_list = FolderList(viewer)
        self.image_list.setMaximumHeight(100)
        self.image_group.glayout.addWidget(self.image_list, 1, 0, 1, 1)

        self.btn_select_mask_folder = QPushButton("Select mask folder")
        self.btn_select_mask_folder.setToolTip("Select mask Folder")
        self.image_group.glayout.addWidget(self.btn_select_mask_folder, 0, 1, 1, 1)

        ##### Elements "Mask list" #####
        self.mask_list = FolderList(viewer)
        self.mask_list.setMaximumHeight(100)
        self.image_group.glayout.addWidget(self.mask_list, 1, 1, 1, 1)

        self.image_group.gbox.setMaximumHeight(self.image_group.gbox.sizeHint().height())

        #### mask options
        self.mask_group = VHGroup('Mask selection', orientation='G')
        self._properties_layout.addWidget(self.mask_group.gbox)
        self.qtext_mask_str = QLineEdit("_mask")
        self.mask_group.glayout.addWidget(QLabel("Mask string"), 0, 0, 1, 1)
        self.mask_group.glayout.addWidget(self.qtext_mask_str, 0, 1, 1, 1)

        self.qtext_model_str = QLineEdit("")
        self.mask_group.glayout.addWidget(QLabel("Model string"), 1, 0, 1, 1)
        self.mask_group.glayout.addWidget(self.qtext_model_str, 1, 1, 1, 1)

        self.mask_group.gbox.setMaximumHeight(self.mask_group.gbox.sizeHint().height())


        '''### Elements "Mask selection"
        self.mask_group = VHGroup('Mask selection', orientation='G')
        self._properties_layout.addWidget(self.mask_group.gbox)

        self.btn_select_mask_folder = QPushButton("Select mask folder")
        self.btn_select_mask_folder.setToolTip("Select mask Folder")
        self.mask_group.glayout.addWidget(self.btn_select_mask_folder, 0, 0, 1, 2)

        ##### Elements "Mask list" #####
        self.mask_list = FolderList(viewer)
        self.mask_group.glayout.addWidget(self.mask_list, 1, 0, 1, 2)

        self.qtext_mask_str = QLineEdit("_mask")
        self.mask_group.glayout.addWidget(QLabel("Mask string"), 2, 0, 1,1)
        self.mask_group.glayout.addWidget(self.qtext_mask_str, 2, 1, 1, 1)

        self.qtext_model_str = QLineEdit("")
        self.mask_group.glayout.addWidget(QLabel("Model string"), 3, 0, 1,1)
        self.mask_group.glayout.addWidget(self.qtext_model_str, 3, 1, 1, 1)'''
        
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
        # load grain sizes for image
        self.btn_load_grainsize_image = QPushButton("Load for image")
        self.btn_load_grainsize_image.setToolTip("Load for image")
        self.analysis_group.glayout.addWidget(self.btn_load_grainsize_image, 3, 0, 1, 1)

        self.mpl_widget = NapariMPLWidget(viewer)
        self.axes = self.mpl_widget.canvas.figure.subplots()
        self.analysis_group.glayout.addWidget(self.mpl_widget.canvas, 0, 1, 4, 1)
        self.analysis_group.glayout.addWidget(self.mpl_widget.toolbar, 4, 1, 1, 2)

        self.combobox_prop_to_plot = create_widget(value = 'area', 
                                                 options={'choices': ['area']},
                                                widget_type='ComboBox')
        self.analysis_group.glayout.addWidget(self.combobox_prop_to_plot.native, 4, 0, 1, 1)

        ### Elements "Display fit"
        self.displayfit_group = VHGroup('Display fit', orientation='G')
        self._properties_layout.addWidget(self.displayfit_group.gbox)

        self.dropdown_fit_method = create_widget(value = 'mask_outline', 
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

        self.btn_plot_dataset = QPushButton("Plot for folder")
        self.btn_plot_dataset.setToolTip("Plot for folder")
        self.grainsize_plot_group.glayout.addWidget(self.btn_plot_dataset)

        self.btn_plot_single_image = QPushButton("Plot for image")
        self.btn_plot_single_image.setToolTip("Plot for image")
        self.grainsize_plot_group.glayout.addWidget(self.btn_plot_single_image)

        self.add_connections()

    def add_connections(self):

        self.image_list.currentItemChanged.connect(self._on_select_image)
        self.btn_select_mask_folder.clicked.connect(self._on_select_mask_folder)
        self.btn_select_image_folder.clicked.connect(self._on_select_image_folder)
        self.btn_run_grainsize_on_folder.clicked.connect(self._on_run_grainsize_on_folder)
        self.btn_run_grainsize_on_image.clicked.connect(self._on_run_grainsize_on_image)
        self.btn_display_fit.clicked.connect(self._on_display_fit)
        self.btn_plot_dataset.clicked.connect(self._on_plot_dataset)
        self.btn_plot_single_image.clicked.connect(self._on_plot_single_image)
        self.combobox_prop_to_plot.changed.connect(self._on_select_prop_to_plot)

        self.btn_load_grainsize.clicked.connect(self._on_load_grainsize)
        self.btn_load_grainsize_image.clicked.connect(self._on_load_grainsize_image)

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

        # reset properties
        self.props_df_dataset = None
        self.props_dataset = None
        self.file_ids = None
        self.df_props = None

        return self.mask_folder

    def _on_run_grainsize_on_folder(self):
        
        composite_name = self.qtext_model_str.text() + self.qtext_mask_str.text()
        self.props_df_dataset, self.props_dataset, self.file_ids = grainsizing.grains_in_dataset(
            data_dir=self.mask_folder, mask_str=composite_name, return_results=True)
        
        self.df_props = pd.concat(self.props_df_dataset)
        self._update_combobox_props(self.df_props.columns)
        self._on_select_prop_to_plot(plot_type='multi')
        
        
    def _update_combobox_props(self, newprops):
        self.combobox_prop_to_plot.changed.disconnect(self._on_select_prop_to_plot)
        self.combobox_prop_to_plot.choices = newprops
        self.combobox_prop_to_plot.changed.connect(self._on_select_prop_to_plot)


    def _on_run_grainsize_on_image(self, event=None):

        self.props_df_image, self.props_image = grainsizing.grains_from_masks(
            masks=self.viewer.layers[Path(self.mask_path).stem].data)
        self._update_combobox_props(self.props_df_image.columns)
        
        self.axes.clear()
        sns.histplot(data=self.props_df_image, x='area', ax=self.axes)
        self.axes.tick_params(axis='both', colors='white')
        self.axes.xaxis.label.set_color('white')
        self.axes.yaxis.label.set_color('white') 
        self.mpl_widget.canvas.figure.canvas.draw()

    def _on_load_grainsize(self, event=None):

        composite_name = self.qtext_model_str.text() + self.qtext_mask_str.text()
        grain_files = data_loader.load_grain_set(file_dir=self.mask_folder, gsd_str=composite_name)
        self.props_df_dataset = read_complete_grain_files(grain_file_list=grain_files)
        # concatenated dataframe of all images
        self.df_props = pd.concat(self.props_df_dataset)
        self._update_combobox_props(self.df_props.columns)
        self._on_select_prop_to_plot(plot_type='multi')

    def _on_load_grainsize_image(self, event=None):
        
        composite_name = self.qtext_model_str.text() + self.qtext_mask_str.text()
        grain_files = data_loader.load_grain_set(file_dir=self.mask_folder, gsd_str=composite_name)
        grain_files = [x for x in grain_files if Path(self.image_name).stem in x]
        
        if len(grain_files) == 0:
            raise ValueError(f'No grain file found for image {self.image_name}')
        elif len(grain_files) > 1:
            raise ValueError(f'Multiple grain files found for image {self.image_name}')
        
        self.props_df_dataset = read_complete_grain_files(grain_file_list=grain_files)
        # concatenated dataframe of all images
        self.df_props = pd.concat(self.props_df_dataset)
        self._update_combobox_props(self.df_props.columns)
        self._on_select_prop_to_plot(plot_type='singke')


    def _on_select_prop_to_plot(self, event=None, plot_type='single'):

        self.axes.clear()
        if plot_type == 'multi':
            sns.histplot(data=self.df_props, x=self.combobox_prop_to_plot.value, ax=self.axes)
        else:
            sns.histplot(data=self.props_df_image, x=self.combobox_prop_to_plot.value, ax=self.axes)
        
        self.axes.tick_params(axis='both', colors='white')
        self.axes.xaxis.label.set_color('white')
        self.axes.yaxis.label.set_color('white')
        self.mpl_widget.canvas.figure.canvas.draw()

    def _on_select_image(self, current_item, previous_item):

        success = self.open_image()
        if not success:
            return False
        else:
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
        self.viewer.open(self.mask_path, layer_type='labels')


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
                self.viewer.layers['axis'].add_polygons(np.array([y,x]).T, edge_color='red')


    def _on_plot_dataset(self):

        grain_files = data_loader.load_grain_set(file_dir=self.mask_folder, gsd_str=self.qtext_model_str.text())
        gsd_l, id_l = grainsizing.gsd_for_set(gsds=grain_files, column='ell: b-axis (px)')

        self.grainsize_axes.clear()
        colors = plt.cm.tab10(np.linspace(0, 1, len(gsd_l)))
        for gsd, id, c in zip(gsd_l, id_l, colors):
            plotting.plot_gsd(gsd=gsd, ax=self.grainsize_axes, gsd_id=id, color=c)
        self.grainsize_axes.tick_params(axis='both', colors='white')
        self.grainsize_axes.xaxis.label.set_color('white')
        self.grainsize_axes.yaxis.label.set_color('white')
        self.grainsize_axes.legend()
        self.grainsize_plot.canvas.figure.canvas.draw()

    def _on_plot_single_image(self):

        grain_files = data_loader.load_grain_set(file_dir=self.mask_folder, gsd_str=self.qtext_model_str.text())
        gsd_l, id_l = grainsizing.gsd_for_set(gsds=grain_files, column='ell: b-axis (px)')

        idx = find_matching_data_index(self.image_path, id_l)
        if len(idx) == 0:
            raise ValueError(f'No mask found for current image {self.image_path}')
        elif len(idx) > 1:
            raise ValueError(f'Multiple masks {idx} found for current image {self.image_path}')
        else:
            idx = idx[0]
        #image_name = self.image_name.split('.')[0]
        #mask_name = [x for x in id_l if image_name in x][0]
        #idx = id_l.index(mask_name)

        self.grainsize_axes.clear()
        plotting.plot_gsd(gsd=gsd_l[idx], ax=self.grainsize_axes)
        self.grainsize_axes.tick_params(axis='both', colors='white')
        self.grainsize_axes.xaxis.label.set_color('white')
        self.grainsize_axes.yaxis.label.set_color('white')
        self.grainsize_plot.canvas.figure.canvas.draw()