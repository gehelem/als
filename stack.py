import os
import cv2
import astroalign as al
import numpy as np
from astropy.io import fits
from tqdm import tqdm
import shutil


def save_tiff(work_path, stack_image, mode="rgb"):
    # invert Red and Blue for cv2

    if mode == "rgb":
        new_stack_image = np.rollaxis(stack_image, 0, 3)
        new_stack_image[:, :, 0] = stack_image[2, :, :]
        new_stack_image[:, :, 2] = stack_image[0, :, :]
    else:
        new_stack_image = stack_image
    cv2.imwrite(work_path + "/stack_image.tiff", new_stack_image)
    print("New image create : %s" % work_path + "/stack_image.tiff")


def create_first_ref_im(work_path, im_path, ref_name):
    # copy first image in work path
    shutil.copy2(im_path, work_path + "/" + ref_name)
    # open ref image
    ref_fit = fits.open(work_path + "/" + ref_name)
    ref = ref_fit[0].data
    ref_fit.close()

    if len(ref.shape) == 2:
        mode = "gray"
    elif len(ref.shape) == 3:
        mode = "rgb"
    else:
        raise ValueError("fit format not support")
    save_tiff(work_path, ref, mode=mode)


def stack_live(work_path, new_image, ref_name, save_im=True):

    if new_image.find(".fits") == -1:
        extension = ".fit"
    else:
        extension = ".fits"
    name = new_image.replace(extension, '')

    # open new image
    new_fit = fits.open(new_image)
    new = new_fit[0].data
    new_fit.close()

    # search type
    new_type = new.dtype.name
    if new_type == 'uint8':
        new_limit = 255
    elif new_type == 'uint16':
        new_limit = 65535
    else:
        raise ValueError("fit format not support")

    if len(new.shape) == 2:
        new_mode = "gray"
    elif len(new.shape) == 3:
        new_mode = "rgb"
    else:
        raise ValueError("fit format not support")

    # open ref image
    ref_fit = fits.open(work_path + "/" + ref_name)
    ref = ref_fit[0].data
    ref_fit.close()
    # search type
    ref_type = ref.dtype.name
    if ref_type == 'uint8':
        ref_limit = 255
    elif ref_type == 'uint16':
        ref_limit = 65535
    else:
        raise ValueError("format not support")

    if len(ref.shape) == 2:
        ref_mode = "gray"
    elif len(ref.shape) == 3:
        ref_mode = "rgb"
    else:
        raise ValueError("fit format not support")

    # format verification
    if ref_limit != new_limit:
        raise ValueError("ref image and new image is not same format")
    if ref_mode == new_mode:
        mode = ref_mode
    else:
        raise ValueError("ref image and new image is not same format")


    # choix rgb ou gray scale
    if mode == "rgb":
        # alignement
        p, __ = al.find_transform(new[1], ref[1])
        # stacking
        stack_image = []
        for j in tqdm(range(3)):
            stack_image.append(al.apply_transform(p, new[j], ref[j]) + ref[j])
            stack_image[j] = np.where(stack_image[j] < ref_limit, stack_image[j], ref_limit)

    elif mode == "gray":
        # alignement
        p, __ = al.find_transform(new, ref)
        # stacking
        stack_image = al.apply_transform(p, new, ref) + ref
        stack_image = np.where(stack_image < ref_limit, stack_image, ref_limit)
    else:
        raise ValueError("Mode not support")

    # save new stack ref image in fit
    os.remove(work_path + "/" + ref_name)
    red = fits.PrimaryHDU(data=stack_image)
    red.writeto(work_path + "/" + ref_name)
    if save_im:
        # save stack image in fit
        red = fits.PrimaryHDU(data=stack_image)
        red.writeto(work_path + "/stack_image_" + name + extension)

    # save stack image in tiff (print image)
    os.remove(work_path + "/stack_image.tiff")
    save_tiff(work_path, np.array(stack_image), mode=mode)

    return 1
