from typing import TYPE_CHECKING
from pathlib import Path

from qtpy.QtWidgets import QVBoxLayout, QPushButton, QWidget, QFileDialog
from .folder_list_widget import FolderList

if TYPE_CHECKING:
    import napari


class ImageGrainProcWidget(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer
        self.setLayout(QVBoxLayout())

        self.file_list = FolderList(viewer)
        self.layout().addWidget(self.file_list)

        self.btn_select_file_folder = QPushButton("Select folder")
        self.layout().addWidget(self.btn_select_file_folder)
        
        self.add_connections()

    def add_connections(self):

        self.file_list.currentItemChanged.connect(self._on_select_file)
        self.btn_select_file_folder.clicked.connect(self._on_click_select_file_folder)


    def _on_click_select_file_folder(self):
        """Interactively select folder to analyze"""

        file_folder = Path(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        self.file_list.update_from_path(file_folder)
        self.reset_channels = True

    def _on_select_file(self, current_item, previous_item):
        
        success = self.open_file()
        if not success:
            return False
        
    def open_file(self):

        # clear existing layers.
        while len(self.viewer.layers) > 0:
            self.viewer.layers.clear()

        # if file list is empty stop here
        if self.file_list.currentItem() is None:
            return False
        
        # open image
        image_name = self.file_list.currentItem().text()
        image_path = self.file_list.folder_path.joinpath(image_name)

        self.viewer.open(image_path)