import shutil
import os
from pathlib import Path
from qtpy.QtWidgets import QListWidget
from qtpy.QtCore import Qt
from natsort import natsorted


class FolderList(QListWidget):
    # be able to pass the Napari viewer name (viewer)
    def __init__(self, viewer, parent=None, file_extensions=['.png', '.jpg','.tif', '.tiff', '.170223']):
        super().__init__(parent)

        self.viewer = viewer
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

        self.folder_path = None

        self.file_extensions = file_extensions

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
            if (f[0] != '.') and (self.folder_path.joinpath(f).is_file()) and (Path(f).suffix in self.file_extensions):
                self.addItem(f)
    
    def addFileEvent(self):
        pass

    def select_first_file(self):
        
        self.setCurrentRow(0)