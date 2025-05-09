import os,pickle, cv2, shutil
import numpy as np
import pandas as pd

from pathlib import Path
from cellpose import io
from tqdm import tqdm
from glob import glob
from natsort import natsorted
from skimage.measure import label, regionprops_table

from cellpose import metrics, models, io
from imagegrains import grainsizing, data_loader, plotting



"""def predict_single_image(image_path,model,image_format='jpg',filter_str='',channels=[0,0],diameter=None,
                         min_size=15,rescale=None,config=None,tar_dir='',return_results=False,save_masks=True,
                         mute=False,model_id=''):
    '''
    Generates a segmentation mask for an individual image and offers the option to save this mask as a .tif-file.
    Code is adapted from segmentation_helper.predict_folder.
    '''

    image_path = str(Path(image_path).as_posix()) #ensure that Path is a string for cellpose classes
    mask_l,flow_l,styles_l,id_list,img_l = [],[],[],[],[]
    try:
        #file_list = natsorted(glob(image_path+'/*'+filter_str+'*.'+image_format))
        #file_list = natsorted(glob(f'{Path(image_path)}/*{filter_str}*.{image_format}'))
        #if mute== False:
        #    print('Predicting for ',image_path,'...')
        #count=0
        #for file in tqdm(file_list,desc=str(image_path),unit='image',colour='CYAN'):
        #for idx in trange(len(file_list), desc=image_path,unit='image',colour='CYAN'):               
        #for idx, file in enumerate(tqdm(file_list)):
        img= io.imread(str(image_path))
        img_id = Path(image_path).stem
        #img_id = file_list[im_idx].split('\\')[len(file_list[im_idx].split('\\'))-1].split('.')[0]
        #if any(x in img_id for x in ['flow','flows','masks','mask','pred','composite']):
        #    continue
        if config:
            try:
                eval_str = ''
                for key,val in config.items():
                    if not eval_str:
                        i_str=f'{key}={val}'
                    else:
                        i_str=f',{key}={val}'
                    eval_str+=i_str
                exec(f'masks, flows, styles = model.eval(img, diameter=diameter,rescale=rescale,min_size=min_size,channels=channels, {eval_str})')
            except AttributeError:
                print('Config file is not formatted correctly. Please check the documentation for more information.')
            except SyntaxError:
                print('Diameter,rescale,min_size,channels are not allowed to be overwritten.')
        else:
            masks, flows, styles = model.eval(img, diameter=diameter,rescale=rescale,min_size=min_size,channels=channels); 
        if save_masks == False and return_results == False:
            print('Saving and returning of results were switched of - therefore mask saving was turned on!')
            save_masks = True
        if save_masks == True:
            if tar_dir:
                os.makedirs(Path(tar_dir), exist_ok=True)
                #filepath = Path(tar_dir) / f'{img_id}_{model_id}_pred.tif'
                io.imsave(f'{tar_dir}/{img_id}_{model_id}_pred.tif',masks)
            else:
                #filepath = Path(image_path) / f'{img_id}_{model_id}_pred.tif'
                io.imsave(f'{image_path}_{img_id}_{model_id}_pred.tif',masks)
        if return_results == True:
            mask_l.append(masks)
            flow_l.append(flows)
            styles_l.append(styles)
            id_list.append(img_id)
            #img_l = [file_list[x] for x in range(len(file_list))]
        #count+=1
        if mute== False:
            print('Sucessfully created predictions for one image(s).')
    except KeyboardInterrupt:
        print('Aborted.')
    return mask_l,flow_l,styles_l,id_list,img_l"""

def predict_single_image(image_path, model,channels=[0,0], diameter=None,
                         min_size=15, rescale=None, config=None, return_results=False,
                         mute=False, save_masks=True,tar_dir='',model_id=''):
    """
    Segment one or multiple images with a trained model.

    Parameters:
    ------------
    image_path (str, Path) - Input image(s)
    model (obj) - Trained model from 'models.CellposeModel' class. 
        Use either `models.CellposeModel(model_type='')` for built-in cellpose models or 
        `models.CellposeModel(pretrained_model='') for custom models.
        See https://cellpose.readthedocs.io/en/latest/models.html for more details
    channels (list (optional, default [0,0])) - channels to use for segmentation
    diameter (float (optional, default None)) - diameter of the objects to segment
    min_size (int (optional, default 15)) - minimum size of the objects to segment
    rescale (float (optional, default None)) - rescale factor for the image
    config (dict (optional, default None)) - dictionary of advanced parameters to be handed down to `CellposeModel.eval()` where keys are parameters and values are parameter values.
    return_results (bool (optional, default False)) - flag for returning predicted masks, flows and styles
    mute (bool (optional, default=False)) - flag for muting console output
    save_masks (bool (optional, default True)) - flag for saving predicted mask as `.tif` files in `tar_dir`
    tar_dir (str (optional, default '')) - The directory to save the predicted masks to.
    model_id (str (optional, default = '')) - optional model name that will be written into output file names
    """

    if not isinstance(image_path, list):
        image_path = [str(Path(image_path).as_posix())]
    else:
        image_path = [str(Path(x).as_posix()) for x in image_path]

    try:
        img = [io.imread(str(x)) for x in image_path]
        img_id = [Path(x).stem for x in image_path]
        
        if config:
            try:
                eval_str = ''
                for key,val in config.items():
                    if not eval_str:
                        i_str=f'{key}={val}'
                    else:
                        i_str=f',{key}={val}'
                    eval_str+=i_str
                exec(f'masks, flows, styles = model.eval(img, diameter=diameter,rescale=rescale,min_size=min_size,channels=channels, {eval_str})')
            except AttributeError:
                print('Config file is not formatted correctly. Please check the documentation for more information.')
            except SyntaxError:
                print('Diameter,rescale,min_size,channels are not allowed to be overwritten.')
        else:
            masks, flows, styles = model.eval(img, diameter=diameter, rescale=rescale, min_size=min_size, channels=channels); 
        
        # save masks
        if save_masks == False and return_results == False:
            print('Saving and returning of results were switched of - therefore mask saving was turned on!')
            save_masks = True
        if save_masks == True:
            if tar_dir:
                os.makedirs(Path(tar_dir), exist_ok=True)
                parent_folder = Path(tar_dir)
            else:
                parent_folder = Path(image_path[0]).parent.joinpath('predictions')
                os.makedirs(parent_folder, exist_ok=True)
            
            for ind, id in enumerate(img_id):
                io.imsave(parent_folder.joinpath(f'{id}_{model_id}_pred.tif'),masks[ind])

        if mute== False:
            print('Sucessfully created predictions for one image(s).')
    except KeyboardInterrupt:
        print('Aborted.')
    
    if return_results == True:
        return masks, flows, styles
    else:
        return None