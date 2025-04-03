from pathlib import Path
from glob import glob
from natsort import natsorted
from warnings import warn
import pandas as pd
import numpy as np


def find_matching_data_index(reference_path, data_name_list, key_string=None):
    """
    Given a reference_path for an image and a data_name_list, 
    find the index of the data in the data_name_list that contains 
    the reference_path file name. Optionally a key_string can be provided to
    specify a specific string that should be contained in the data_name_list items.
    
    Typical usage: find the matching mask in a list of mask names 
    matching the image name.

    Parameters
    ----------
    reference_path : str or Path
        Path to the reference image.
    image_name_list : list
        List of image names.
    key_string : str, optional
        Specific string that should be contained in the data_name_list items. 
        The default is None.
    """
    
    reference_name = Path(reference_path).stem
    match_index = [i for i in range(len(data_name_list)) if reference_name in data_name_list[i]]
    if key_string:
        match_index = [i for i in match_index if key_string in data_name_list[i]]

    return match_index

def find_match_in_folder(folder, image_name, model_str, data_str, data_format):
    """
    Find the matching data in a folder given an image name, data specific string and format.
    It is epxected that data is of the form image_name+data_str+data_format.
    Typical usage: find the matching mask in a folder of masks matching the image name.

    Parameters
    ----------
    folder : str or Path
        Path to the folder containing the data.
    image_name : str
        Name of the image.
    model_str  : str
        Model specific string (like 'fh_boosted')
    data_str : str
        Data specific string (like 'pred')
    data_format : str
        Data format.

    Returns
    -------
    data : str
        Path to the data.
    
    """

    mask_list = natsorted(glob(f'{folder}/{Path(image_name).stem}*{model_str}*{data_str}*.{data_format}'))
    if len(mask_list) == 0:
        # raise warning that no image is found with warning. import warning if necessary
        warn(f'No mask found in {folder} matching {Path(image_name).stem}*{model_str}*{data_str}*.{data_format}')
        mask = None
    elif len(mask_list) > 1:
        warn(f'Multiple masks found in {folder} matching {Path(image_name).stem}*{model_str}*{data_str}*.{data_format}. Using the first one.')
        mask = mask_list[0]
    else:
        mask = mask_list[0]
    
    return mask

def read_complete_grain_files(grain_file_list):
    """
    Read the complete grain files and return a list of dictionaries containing the data.

    Parameters
    ----------
    grain_file_list : list
        List of grain file paths.

    Returns
    -------
    grains : list
        List of pandas dataframes containing the data.
    """
    
    grains = []
    for grain_file in grain_file_list:
        try:
            grains.append(pd.read_csv(grain_file))
        except Exception as e:
            warn(f'Could not read {grain_file} with error {e}')

    return grains

def compute_average_ap(evals):

    all_ap = np.stack([x['ap'] for x in evals.values()])
    avg_l = np.mean(all_ap, axis=0)
    std_l = np.std(all_ap, axis=0)
    std_ul = avg_l + std_l
    std_ll = avg_l - std_l
    return avg_l, std_l, std_ul, std_ll