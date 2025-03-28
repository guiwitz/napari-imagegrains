from typing import TYPE_CHECKING
from pathlib import Path
from glob import glob
from natsort import natsorted

from magicgui.widgets import create_widget
from qtpy.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QTabWidget,
                            QLabel, QFileDialog, QLineEdit)
import pandas as pd
import seaborn as sns
import numpy as np
from napari_matplotlib.base import NapariMPLWidget

from .imgr_proc_widget import VHGroup
from .folder_list_widget import FolderList
from imagegrains import grainsizing, data_loader, plotting

if TYPE_CHECKING:
    import napari


class ImageGrainStatsWidget(QWidget):
    """Widget for grain size analysis"""

    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        
        self.viewer = viewer
        #self.setLayout(QVBoxLayout())

        self.props_df_image = None
        self.props_image = None
        self.props_df_dataset = None
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
        self.image_group.glayout.addWidget(self.btn_select_image_folder, 0, 0, 1, 2)

        ##### Elements "Image list" #####
        self.image_list = FolderList(viewer)
        self.image_group.glayout.addWidget(self.image_list, 1, 0, 1, 2)


        ### Elements "Mask selection"
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
        
        ### Elements "Analysis"
        self.analysis_group = VHGroup('Analysis', orientation='G')
        self._properties_layout.addWidget(self.analysis_group.gbox)

        self.btn_run_grainsize_on_folder = QPushButton("Run on folder")
        self.btn_run_grainsize_on_folder.setToolTip("Run grain measure on folder")
        self.analysis_group.glayout.addWidget(self.btn_run_grainsize_on_folder)

        self.btn_run_grainsize_on_image = QPushButton("Run on image")
        self.btn_run_grainsize_on_image.setToolTip("Run grain measure on image")
        self.analysis_group.glayout.addWidget(self.btn_run_grainsize_on_image)

        self.mpl_widget = NapariMPLWidget(viewer)
        self.axes = self.mpl_widget.canvas.figure.subplots()
        self.analysis_group.glayout.addWidget(self.mpl_widget.canvas)
        self.analysis_group.glayout.addWidget(self.mpl_widget.toolbar)

        ### Elements "Display fit"
        self.displayfit_group = VHGroup('Display fit', orientation='G')
        self._properties_layout.addWidget(self.displayfit_group.gbox)

        self.dropdown_fit_method = create_widget(value = 'convex_hull', 
                                                 options={'choices': ['convex_hull', 'mask_outline']},
                                                widget_type='ComboBox')
        self.displayfit_group.glayout.addWidget(self.dropdown_fit_method.native)
        self.btn_display_fit = QPushButton("Display fit")
        self.btn_display_fit.setToolTip("Display fit")
        self.displayfit_group.glayout.addWidget(self.btn_display_fit)

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

        self.btn_plot_dataset = QPushButton("Plot dataset")
        self.btn_plot_dataset.setToolTip("Plot dataset")
        self.grainsize_plot_group.glayout.addWidget(self.btn_plot_dataset)

        self.add_connections()

    def add_connections(self):

        self.image_list.currentItemChanged.connect(self._on_select_image)
        self.btn_select_mask_folder.clicked.connect(self._on_select_mask_folder)
        self.btn_select_image_folder.clicked.connect(self._on_select_image_folder)
        self.btn_run_grainsize_on_folder.clicked.connect(self._on_run_grainsize_on_folder)
        self.btn_run_grainsize_on_image.clicked.connect(self._on_run_grainsize_on_image)
        self.btn_display_fit.clicked.connect(self._on_display_fit)
        self.btn_plot_dataset.clicked.connect(self._on_plot_dataset)

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

        return self.mask_folder

    def _on_run_grainsize_on_folder(self):
        self.props_df_dataset, self.props_dataset, self.file_ids = grainsizing.grains_in_dataset(
            data_dir=self.mask_folder, mask_str=self.qtext_mask_str.text(), return_results=True)
        
        df_props = pd.concat(self.props_df_dataset)

        self.axes.clear()
        sns.histplot(data=df_props, x='area', ax=self.axes)
        self.axes.tick_params(axis='both', colors='white')
        self.mpl_widget.canvas.figure.canvas.draw()

    def _on_run_grainsize_on_image(self, event=None):

        self.props_df_image, self.props_image = grainsizing.grains_from_masks(
            masks=self.viewer.layers[Path(self.mask_path).stem].data)
        
        self.axes.clear()
        sns.histplot(data=self.props_df_image, x='area', ax=self.axes)
        self.axes.tick_params(axis='both', colors='white')
        self.axes.xaxis.label.set_color('white')
        self.axes.yaxis.label.set_color('white') 
        self.mpl_widget.canvas.figure.canvas.draw()


    def _on_select_image(self, current_item, previous_item):

        success = self.open_image()
        if not success:
            return False
        else:
            mask_str = self.qtext_mask_str.text()
            mask_format = 'tif'
            self.mask_path = None
            mask_list = natsorted(glob(f'{self.mask_folder}/{Path(self.image_name).stem}*{mask_str}*.{mask_format}'))
            if len(mask_list) > 0:
                self.mask_path = mask_list[0]
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

        self.viewer.open(self.mask_path, layer_type='labels')


    def _on_display_fit(self):
        
        if self.props_df_dataset is None:
            if self.props_image is None:
                self._on_run_grainsize_on_image()
            current_props = self.props_image
        else:
            im_name = Path(self.image_name).stem
            match_image = [i for i in range(len(self.file_ids)) if im_name in self.file_ids[i]]
            if len(match_image) != 1:
                print('Image not found in dataset')
                return
            current_props = self.props_dataset[match_image[0]]

        padding_size = 2
        _,_,a_coords,b_coords = grainsizing.fit_grain_axes(current_props, method=self.dropdown_fit_method.value,padding_size=padding_size)

        if 'contours' in self.viewer.layers:
            self.viewer.layers['contours'].clear()
        else:
            self.viewer.add_shapes(name='contours', face_color=[0,0,0,0], edge_color='orange')
        
        if 'axis' in self.viewer.layers:
            self.viewer.layers['axis'].clear()
        else:
            self.viewer.add_shapes(name='axis', face_color=[0,0,0,0], edge_color='red')

        for _idx in range(len(current_props)):
            miny, minx, maxy, maxx = current_props[_idx].bbox

            img_pad = grainsizing.image_padding(current_props[_idx].image,padding_size=padding_size)
            contours = grainsizing.contour_grain(img_pad)
            for contour in contours:
                self.viewer.layers['contours'].add_polygons([np.array(contour) + np.array([-(padding_size-.5)+miny, -(padding_size-.5)+minx])])
                self.viewer.layers['axis'].add_lines([np.array(a_coords[_idx]) + np.array([-(padding_size-.5)+miny, -(padding_size-.5)+minx])], edge_color='red')
                self.viewer.layers['axis'].add_lines([np.array(b_coords[_idx]) + np.array([-(padding_size-.5)+miny, -(padding_size-.5)+minx])], edge_color='blue')

    def _on_plot_dataset(self):

        grain_files = data_loader.load_grain_set(file_dir=self.mask_folder, gsd_str='pred_grains')
        gsd_l, id_l = grainsizing.gsd_for_set(gsds=grain_files, column='ell: b-axis (px)')

        image_name = self.image_name.split('.')[0]
        mask_name = [x for x in id_l if image_name in x][0]
        idx = id_l.index(mask_name)

        self.grainsize_axes.clear()
        plotting.plot_gsd(gsd=gsd_l[idx], ax=self.grainsize_axes)
        self.grainsize_axes.tick_params(axis='both', colors='white')
        self.grainsize_axes.xaxis.label.set_color('white')
        self.grainsize_axes.yaxis.label.set_color('white') 
        self.grainsize_plot.canvas.figure.canvas.draw()