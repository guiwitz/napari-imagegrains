import shutil
import os
from pathlib import Path
from qtpy.QtWidgets import QListWidget
from qtpy.QtCore import Qt
from natsort import natsorted
import re


class FolderList(QListWidget):
    # be able to pass the Napari viewer name (viewer)

    def __init__(self, viewer, parent=None, file_extensions=None):
        super().__init__(parent)

        self.viewer = viewer
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

        self.folder_path = None

        self.file_extensions = file_extensions
        # self.digit_extension = self.generate_digit_extension()
        # self.file_extensions.append(".170223")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):

        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            
            for url in event.mimeData().urls():
                file = str(url.toLocalFile())
                if not Path(file).is_dir():
                    self.update_from_path(Path(file).parent)
                    file_list = [self.item(x).text() for x in range(self.count())]
                    self.setCurrentRow(file_list.index(Path(file).name))
                else:
                    self.update_from_path(Path(file))

    def update_from_path(self, path):

        self.clear()
        self.folder_path = path
        files = os.listdir(self.folder_path)
        files = natsorted(files)
        for f in files:
            if (f[0] != '.') and (self.folder_path.joinpath(f).is_file()):
                if Path(f).suffix[1:].isdigit():
                    if self.file_extensions == None:
                        self.addItem(f)
                else:
                    if self.file_extensions != None and Path(f).suffix in self.file_extensions:
                        self.addItem(f)

    
    def addFileEvent(self):
        pass

    def select_first_file(self):
        
        self.setCurrentRow(0)
    