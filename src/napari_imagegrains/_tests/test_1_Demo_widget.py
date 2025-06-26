import pytest

def test_1_Demo_widget(make_napari_viewer):
    #!/usr/bin/env python
    # coding: utf-8

    # # napari-imagegrains demo

    # To get started without having to first setup a dataset, find the correct widget etc. we provide a demo widget that will allow to download a demo dataset, models and open the first processing widget for you. For that, head to `Plugins -> ImageGrains -> ImageGrain Demo Widget. You should see the following window appear:

    # In[1]:


    # get_ipython().run_line_magic('load_ext', 'autoreload')
    # get_ipython().run_line_magic('autoreload', '2')


    # In[2]:


    import napari
    from napari_imagegrains.imgr_demodata_widget import ImageGrainDemoWidget
    from pathlib import Path
    import shutil


    # In[3]:


    demodata_folder = Path.home().joinpath("imagegrains/")
    if demodata_folder.exists() and demodata_folder.is_dir():
        shutil.rmtree(demodata_folder)


    # In[4]:


    viewer = make_napari_viewer()
    self = ImageGrainDemoWidget(viewer=viewer)
    viewer.window.add_dock_widget(self);


    # In[5]:


    napari.utils.NotebookScreenshot(viewer)


    # Now click on `Download demo data` and you should see the following:

    # In[6]:


    self._on_click_download_demodata()
    napari.utils.NotebookScreenshot(viewer)


    # For the next steps, head to the documentation for the `ImageGrain Processing Widget`.


if __name__ == "__main__":
    _Demo_widget(make_napari_viewer)
