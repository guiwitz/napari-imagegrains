import cv2
from pathlib import Path


class SegmentationWidget():
    
    def __init__(self, image_path):

        self.selected_image_path = image_path
    
    def gray_image(self):
        self.image_loaded = cv2.imread(self.selected_image_path)
        self.image_gray = cv2.cvtColor(self.image_loaded, cv2.COLOR_RGB2GRAY)
        return self.image_gray