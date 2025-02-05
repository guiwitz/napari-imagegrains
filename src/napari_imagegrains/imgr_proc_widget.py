from typing import TYPE_CHECKING
from pathlib import Path

from qtpy.QtWidgets import QVBoxLayout, QPushButton, QWidget, QFileDialog

from .folder_list_widget import FolderList
from .segment_image_widget import SegmentationWidget

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

        image_folder = Path(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        self.image_list.update_from_path(image_folder)
        self.reset_channels = True
    

    def _on_click_select_model_folder(self):
        """Interactively select folder to analyze"""

        model_folder = Path(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        self.model_list.update_from_path(model_folder)
        self.reset_channels = True
    

    def _on_click_segment_image(self):
        """
        Segment image. In development...
        """
        try:
            self.segmentation_widget = SegmentationWidget(self.image_path)
            self.segmented = self.segmentation_widget.gray_image()
            # while len(self.viewer.layers) > 1:
            #     self.viewer.layers.clear()
            self.viewer.add_image(self.segmented, name=f"segmented_{self.image_name}")
        except:
            pass


    def _on_select_image(self, current_item, previous_item):
        
        success = self.open_image()
        if not success:
            return False
        else:
            return self.image_path
    
    def _on_select_model(self, current_item, previous_item):
        
        success = print("Model was selected")
        if not success:
            return False
        

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