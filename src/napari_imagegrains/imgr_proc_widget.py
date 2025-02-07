import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


from typing import TYPE_CHECKING
from pathlib import Path

from qtpy.QtWidgets import QVBoxLayout, QPushButton, QWidget, QFileDialog

from .folder_list_widget import FolderList
from .access_single_image_widget import predict_single_image

from imagegrains import data_loader, segmentation_helper, plotting
from cellpose import models
import matplotlib.pyplot as plt

import warnings
warnings.filterwarnings("ignore")




if TYPE_CHECKING:
    import napari


class ImageGrainProcWidget(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer
        self.setLayout(QVBoxLayout())

        self.image_list = FolderList(viewer)
        self.layout().addWidget(self.image_list)
        self.btn_select_image_folder = QPushButton("Select image folder")
        self.layout().addWidget(self.btn_select_image_folder)
        
        self.model_list = FolderList(viewer)
        self.layout().addWidget(self.model_list)
        self.btn_select_model_folder = QPushButton("Select model folder")
        self.layout().addWidget(self.btn_select_model_folder)

        self.btn_segment_image = QPushButton("Segment image")
        self.layout().addWidget(self.btn_segment_image)
        
        self.add_connections()


    def add_connections(self):

        self.image_list.currentItemChanged.connect(self._on_select_image)
        self.model_list.currentItemChanged.connect(self._on_select_model)
        self.btn_select_image_folder.clicked.connect(self._on_click_select_image_folder)
        self.btn_select_model_folder.clicked.connect(self._on_click_select_model_folder)
        self.btn_segment_image.clicked.connect(self._on_click_segment_image)


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
    

    def _on_click_segment_image(self):
        """
        Segment image. In development...
        """
        model_path = self.model_path

        model = models.CellposeModel(gpu=False, pretrained_model=str(model_path))

        # image folder
        #image_path = self.image_folder
        #self.mask_l, self.flow_l, self.styles_l, self.id_list, self.img_l = segmentation_helper.predict_folder(image_path,model,mute=True,return_results=True,save_masks=True, tar_dir="masks/", model_id='fh_boosted_1')

        # single image:
        image_path = self.image_path
        self.mask_l, self.flow_l, self.styles_l, self.id_list, self.img_l = predict_single_image(image_path,model,mute=True,return_results=True,save_masks=True, tar_dir="masks/", model_id='fh_boosted_1')


        self.viewer.add_labels(self.mask_l[0], name=f"segmented_{self.image_name}")



    def _on_select_image(self, current_item, previous_item):
        
        success = self.open_image()
        if not success:
            return False
        else:
            return self.image_path
    
    def _on_select_model(self, current_item, previous_item):

        # if file list is empty stop here
        if self.model_list.currentItem() is None:
            return False
        
        # extract model path
        self.model_name = self.model_list.currentItem().text()
        self.model_path = self.model_list.folder_path.joinpath(self.model_name)
        print(self.model_path)
        
        return self.model_path
        

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

        self.viewer.open(self.image_path)