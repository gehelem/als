# ALS - Astro Live Stacker
# Copyright (C) 2019  Sébastien Durand (Dragonlost) - Gilles Le Maréchal (Gehelem)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import cv2
import astroalign as al
import numpy as np
from astropy.io import fits
from tqdm import tqdm

name_of_tiff_image = "stack_image.tiff"
name_of_fit_image = "stack_ref_image.fit"


def save_tiff(work_path, stack_image, mode="rgb"):
    # invert Red and Blue for cv2

    if mode == "rgb":
        new_stack_image = np.rollaxis(stack_image, 0, 3)
        cv2.imwrite(work_path + "/" + name_of_tiff_image, cv2.cvtColor(new_stack_image, cv2.COLOR_RGB2BGR))
    else:
        new_stack_image = stack_image
        cv2.imwrite(work_path + "/" + name_of_tiff_image, new_stack_image)
    print("TIFF image create : %s" % work_path + "/" + name_of_tiff_image)


def test_and_debayer_to_rgb(header, image):
    if len(image.shape) == 2 and not ("BAYERPAT" in header):
        print("B&W mode...")
        new_mode = "gray"
    elif len(image.shape) == 3:
        print("RGB mode...")
        new_mode = "rgb"
    elif len(image.shape) == 2 and "BAYERPAT" in header:
        print("debayering...")
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
        limit = 2.**8-1
    elif im_type == 'uint16':
        limit = 2.**16-1
    else:
        raise ValueError("fit format not support")

    return limit, im_type


def create_first_ref_im(work_path, im_path, ref_name, save_im=False):
    # cleaning work folder
    import os
    if os.path.exists(os.path.expanduser(work_path + "/" + name_of_fit_image)):
        os.remove(os.path.expanduser(work_path + "/" + name_of_fit_image))
    else:
        print("The file does not exist")

    # test image format ".fit" or ".fits"
    if im_path.find(".fits") == -1:
        extension = ".fit"
    else:
        extension = ".fits"
    # remove extension
    name = im_path.replace(extension, '')
    # remove path
    name = name[name.rfind("/") + 1:]

    # open ref image
    ref_fit = fits.open(im_path)
    ref = ref_fit[0].data
    # save header
    ref_header = ref_fit[0].header
    ref_fit.close()
    # test rgb or gray
    ref, mode = test_and_debayer_to_rgb(ref_header, ref)
    red = fits.PrimaryHDU(data=ref)
    red.writeto(work_path + "/" + ref_name)
    red.writeto(work_path + "/" + "first_" + ref_name)

    save_tiff(work_path, ref, mode=mode)

    if save_im:
        # save stack image in fit
        red.writeto(work_path + "/" + "stack_image_" + name + extension)


def stack_live(work_path, new_image, ref_name, counter, save_im=False, align=True, stack_methode="Sum"):

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

    if align:
        # open first ref image (for align)
        first_ref_fit = fits.open(work_path + "/" + "first_" + ref_name)
        first_ref = first_ref_fit[0].data
        first_ref_fit.close()

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
    print("alignement and stacking...")
    if mode == "rgb":
        if align:
            # alignement
            p, __ = al.find_transform(new[1], first_ref[1])
        # stacking
        stack_image = []
        for j in tqdm(range(3)):
            if align:
                align_image = al.apply_transform(p, new[j], ref[j])
            else:
                align_image = new[j]

            if stack_methode == "Sum":
                stack = np.float32(align_image) + np.float32(ref[j])
            elif stack_methode == "Mean":
                stack = ((counter - 1) * np.float32(ref[j]) + np.float32(align_image)) / counter

            if im_type == 'uint8':
                stack_image.append(np.uint8(np.where(stack < 2 ** 8 - 1, stack, 2 ** 8 - 1)))
            elif im_type == 'uint16':
                stack_image.append(np.uint16(np.where(stack < 2 ** 16 - 1, stack, 2 ** 16 - 1)))
            else:
                raise ValueError("Stack method is not support")

    elif mode == "gray":
        if align:
            # alignement
            p, __ = al.find_transform(new, first_ref)
            align_image = al.apply_transform(p, new, ref)
        else:
            align_image = new

        # stacking
        if stack_methode == "Sum":
            stack = np.float32(align_image) + np.float32(ref)
        elif stack_methode == "Mean":
            stack = ((counter - 1) * np.float32(ref) + np.float32(align_image)) / counter
        else:
            raise ValueError("Stack method is not support")

        if im_type == 'uint8':
            stack_image = np.uint8(stack)
        elif im_type == 'uint16':
            stack_image = np.uint16(stack)

    else:
        raise ValueError("Mode not support")

    # save new stack ref image in fit
    os.remove(work_path + "/" + ref_name)
    red = fits.PrimaryHDU(data=stack_image)
    red.writeto(work_path + "/" + ref_name)
    if save_im:
        # save stack image in fit
        red = fits.PrimaryHDU(data=stack_image)
        red.writeto(work_path + "/" + "stack_image_" + name + extension)

    # save stack image in tiff (print image)
    os.remove(work_path + "/" + name_of_tiff_image)
    save_tiff(work_path, np.array(stack_image), mode=mode)

    return 1
