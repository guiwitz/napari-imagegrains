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



def predict_single_image(image_path,model,image_format='jpg',filter_str='',channels=[0,0],diameter=None,
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
    return mask_l,flow_l,styles_l,id_list,img_l