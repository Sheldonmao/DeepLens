import os
import cv2 as cv
import random 
import numpy as np
import torch
import torch.nn as nn
from torchvision.utils import save_image
from PIL import Image
from torchvision import transforms
import matplotlib.pyplot as plt
from skimage.metrics import peak_signal_noise_ratio as compare_psnr
from skimage.metrics import structural_similarity as compare_ssim
from scipy.ndimage.filters import gaussian_filter
import lpips
import torch.nn.functional as F
import logging
import string
from tqdm import tqdm
from datetime import datetime

# ==================================
# Image batch quality evaluation
# ==================================

def batch_PSNR(img_clean, img):
    """ Compute PSNR for image batch.
    """
    Img = img.mul(255).add_(0.5).clamp_(0, 255).to('cpu', torch.uint8).numpy()
    Img_clean = img_clean.mul(255).add_(0.5).clamp_(0, 255).to('cpu', torch.uint8).numpy()
    PSNR = 0
    for i in range(Img.shape[0]):
        PSNR += compare_psnr(Img_clean[i,:,:,:], Img[i,:,:,:])
    return round(PSNR/Img.shape[0], 4)


def batch_SSIM(img, img_clean, multichannel=True):
    """ Compute SSIM for image batch.
    """
    Img = img.mul(255).add_(0.5).clamp_(0, 255).to('cpu', torch.uint8).numpy()
    Img_clean = img_clean.mul(255).add_(0.5).clamp_(0, 255).to('cpu', torch.uint8).numpy()
    SSIM = 0
    for i in range(Img.shape[0]):
        SSIM += compare_ssim(Img_clean[i,...], Img[i,...], channel_axis=0)
    
    return round(SSIM/Img.shape[0], 4)


def batch_LPIPS(img, img_clean):
    """ Compute LPIPS loss.
    """
    device = img.device
    loss_fn = lpips.LPIPS(net='vgg', spatial=True)
    loss_fn.to(device)
    dist = loss_fn.forward(img, img_clean)
    return dist.mean().item()


# ==================================
# Image batch normalization
# ==================================

def normalize_ImageNet_stats(batch):
    """ Normalize dataset by ImageNet(real scene images) distribution. 
    """
    mean = torch.zeros_like(batch)
    std = torch.zeros_like(batch)
    mean[:, 0, :, :] = 0.485
    mean[:, 1, :, :] = 0.456
    mean[:, 2, :, :] = 0.406
    std[:, 0, :, :] = 0.229
    std[:, 1, :, :] = 0.224
    std[:, 2, :, :] = 0.225
    
    batch_out = (batch - mean) / std
    return batch_out


def de_normalize(batch):
    """ Convert normalized images to original images to compute PSNR.
    """
    mean = torch.zeros_like(batch)
    std = torch.zeros_like(batch)
    mean[:, 0, :, :] = 0.485
    mean[:, 1, :, :] = 0.456
    mean[:, 2, :, :] = 0.406
    std[:, 0, :, :] = 0.229
    std[:, 1, :, :] = 0.224
    std[:, 2, :, :] = 0.225
    
    batch_out = batch * std + mean
    return batch_out


# ==================================
def gpu_init(gpu=0):
    """Initialize device and data type.

    Returns:
        device: which device to use.
    """
    device = torch.device(f"cuda:{gpu}" if torch.cuda.is_available() else "cpu")
    print("Using: {}".format(device))
    torch.set_default_tensor_type('torch.FloatTensor')
    return device


def set_seed(seed=0):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    # torch.cuda.manual_seed_all(seed) # if you are using multi-GPU.
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.enabled = False


def set_logger(dir='./'):
    logger = logging.getLogger()
    logger.setLevel('DEBUG')
    BASIC_FORMAT = "%(asctime)s:%(levelname)s:%(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(BASIC_FORMAT, DATE_FORMAT)

    chlr = logging.StreamHandler()
    chlr.setFormatter(formatter)
    chlr.setLevel('INFO')

    fhlr = logging.FileHandler(f"{dir}/output.log")
    fhlr.setFormatter(formatter)
    fhlr.setLevel('INFO')

    # fhlr2 = logging.FileHandler(f"{dir}/error.log")
    # fhlr2.setFormatter(formatter)
    # fhlr2.setLevel('WARNING')

    logger.addHandler(chlr)
    logger.addHandler(fhlr)
    # logger.addHandler(fhlr2)
