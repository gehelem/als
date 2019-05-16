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
        cv2.imwrite(work_path + "/stack_image.tiff", cv2.cvtColor(new_stack_image, cv2.COLOR_RGB2BGR))
    else:
        new_stack_image = stack_image
        cv2.imwrite(work_path + "/stack_image.tiff", new_stack_image)
    print("New image create : %s" % work_path + "/stack_image.tiff")


def test_and_debayer_to_rgb(header, image):
    if len(image.shape) == 2 and not ("BAYERPAT" == header):
        new_mode = "gray"
    elif len(image.shape) == 3:
        new_mode = "rgb"
    elif len(image.shape) == 2 and "BAYERPAT" == header:
        debay = header["BAYERPAT"]
        cv_debay = debay[3] + debay[2]
        if cv_debay == "BG":
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BAYER_BG2RGB)
        elif cv_debay == "GB":
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BAYER_GB2RGB)
        elif cv_debay == "RG":
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BAYER_RG2RGB)
        elif cv_debay == "GR":
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BAYER_GR2RGB)
        else:
            raise ValueError("this debayer option not support")
        image = np.rollaxis(rgb_image, 2, 0)
        new_mode = "rgb"
    else:
        raise ValueError("fit format not support")

    return image, new_mode


def test_utype(image):
    # search type
    im_type = image.dtype.name
    if im_type == 'uint8':
        limit = 2**8-1
    elif im_type == 'uint16':
        limit = 2**16-1
    else:
        raise ValueError("fit format not support")

    return limit, im_type


def create_first_ref_im(work_path, im_path, ref_name):
    # copy first image in work path
    shutil.copy2(im_path, work_path + "/" + ref_name)
    # open ref image
    ref_fit = fits.open(im_path)
    ref = ref_fit[0].data
    # save header
    ref_header = ref_fit[0].header
    ref_fit.close()
    # test rgb or gray
    ref, mode = test_and_debayer_to_rgb(ref_header, ref)

    save_tiff(work_path, ref, mode=mode)


def stack_live(work_path, new_image, ref_name, save_im=True, align=True):

    # test image format ".fit" or ".fits"
    if new_image.find(".fits") == -1:
        extension = ".fit"
    else:
        extension = ".fits"
    # remove extension
    name = new_image.replace(extension, '')
    # remove path
    name = name[name.rfind("/") + 1:]

    # open new image
    new_fit = fits.open(new_image)
    new = new_fit[0].data
    # save header
    new_header = new_fit[0].header
    new_fit.close()
    # test data type
    new_limit, new_type = test_utype(new)
    # test rgb or gray
    new, new_mode = test_and_debayer_to_rgb(new_header, new)

    # open ref image
    ref_fit = fits.open(work_path + "/" + ref_name)
    ref = ref_fit[0].data
    ref_fit.close()
    # test data type
    ref_limit, ref_type = test_utype(ref)

    # test rgb or gray
    if len(ref.shape) == 2:
        ref_mode = "gray"
    elif len(ref.shape) == 3:
        ref_mode = "rgb"
    else:
        raise ValueError("fit format not support")

    # format verification
    if ref_limit != new_limit:
        raise ValueError("ref image and new image is not same format")
    else:
        im_type = ref_type
    if ref_mode == new_mode:
        mode = ref_mode
    else:
        raise ValueError("ref image and new image is not same format")

    # choix rgb ou gray scale
    if mode == "rgb":
        if align:
            # alignement
            p, __ = al.find_transform(new[1], ref[1])
        # stacking
        stack_image = []
        for j in tqdm(range(3)):
            if align:
                if im_type == 'uint8':
                    align_image = np.uint8(al.apply_transform(p, new[j], ref[j]))
                elif im_type == 'uint16':
                    align_image = np.uint16(al.apply_transform(p, new[j], ref[j]))
            else:
                align_image = new[j]
            stack_image.append(align_image+ref[j])

    elif mode == "gray":
        if align:
            # alignement
            p, __ = al.find_transform(new, ref)
        # stacking
        if align:
            if im_type == 'uint8':
                align_image = np.uint8(al.apply_transform(p, new, ref))
            elif im_type == 'uint16':
                align_image = np.uint16(al.apply_transform(p, new, ref))
        else:
            align_image = new
        stack_image = align_image + ref
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
