import os

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, QGridLayout, QLabel, QPushButton
from magicgui.widgets import create_widget
from pathlib import Path

from imagegrains import data_loader

if TYPE_CHECKING:
    import napari

class ImageGrainDemoData(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()

        self.viewer = viewer
        self.default_download_path = Path.home().joinpath("imagegrains")

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.demodata_group = VHGroup('Download Demo Data', orientation='G')
        self.main_layout.addWidget(self.demodata_group.gbox)

        self.lbl_select_download_directory = QLabel("Download directory")
        self.demodata_directory = create_widget(value=self.default_download_path, options={"mode": "d", "label": "Choose a directory"})
        self.custom_download_path = self.demodata_directory.value

        self.btn_download_demodata = QPushButton("Download demo data")
        self.demodata_group.glayout.addWidget(self.lbl_select_download_directory, 0, 0, 1, 1)
        self.demodata_group.glayout.addWidget(self.demodata_directory.native, 0, 1, 1, 1)
        self.demodata_group.glayout.addWidget(self.btn_download_demodata, 1, 0, 1, 2)
    
        self.add_connections()


    def add_connections(self):
        '''Connects GUI elements with execution functions.'''

        self.btn_download_demodata.clicked.connect(self._on_click_download_demodata)
    

    def _on_click_download_demodata(self):
        """Downloads the demo data from Githhub"""

        self.custom_download_path = self.demodata_directory.value

        if self.custom_download_path == self.default_download_path:
            if not os.path.exists(self.default_download_path):
                os.makedirs(self.default_download_path)
        
        data_loader.download_files(self.custom_download_path)



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



# For having the downloaded demo data displayed in the imgr_proc_widget, see the example from:
# https://github.com/guiwitz/napari-sediment/blob/main/src/napari_sediment/data/data_contribution.py

# especially: create_cake()