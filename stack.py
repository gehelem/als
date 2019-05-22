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
import rawpy

name_of_tiff_image = "stack_image.tiff"


def SCNR(rgb_image, im_type, im_limit, rgb_type="RGB", scnr_type="ne_m", amount=0.5):
    # SCNR Average Neutral Protection
    if rgb_type == "RGB":
        red = 0
        blue = 2
    elif rgb_type == "BGR":
        red = 2
        blue = 0

    rgb_image = np.float32(rgb_image)

    if scnr_type == "ne_m":
        m = (rgb_image[red] + rgb_image[blue]) * 0.5
        compare = rgb_image[1] < m
        rgb_image[1] = compare * rgb_image[1] + np.invert(compare) * m

    elif scnr_type == "ne_max":
        compare = rgb_image[red] > rgb_image[blue]
        m = compare * rgb_image[red] + np.invert(compare) * rgb_image[blue]
        compare = rgb_image[1] < m
        rgb_image[1] = compare * rgb_image[1] + np.invert(compare) * m

    elif scnr_type == "ma_ad":
        rgb_image = rgb_image / im_limit
        unity_m = np.ones((rgb_image[1].shape[0], rgb_image[1].shape[1]))
        compare = unity_m < (rgb_image[blue] + rgb_image[red])
        m = compare * unity_m + np.invert(compare) * (rgb_image[blue] + rgb_image[red])
        rgb_image[1] = rgb_image[1] * (1 - amount) * (1 - m) + m * rgb_image[1]
        rgb_image = rgb_image * im_limit

    elif scnr_type == "ma_max":
        rgb_image = rgb_image / im_limit
        compare = rgb_image[red] > rgb_image[blue]
        m = compare * rgb_image[red] + np.invert(compare) * rgb_image[blue]
        rgb_image[1] = rgb_image[1] * (1 - amount) * (1 - m) + m * rgb_image[1]
        rgb_image = rgb_image * im_limit

    if im_type == "uint16":
        rgb_image = np.where(rgb_image < im_limit, rgb_image, im_limit)
        rgb_image = np.uint16(rgb_image)
    elif im_type == "uint8":
        rgb_image = np.where(rgb_image < im_limit, rgb_image, im_limit)
        rgb_image = np.uint8(rgb_image)

    return rgb_image


def save_tiff(work_path, stack_image, mode="rgb", param=[]):
    # invert Red and Blue for cv2

    if mode == "rgb":
        new_stack_image = np.rollaxis(stack_image, 0, 3)
        new_stack_image = cv2.cvtColor(new_stack_image, cv2.COLOR_RGB2BGR)
    else:
        new_stack_image = stack_image

    limit, im_type = test_utype(new_stack_image)

    if param[0] != 1 or param[1] != 0 or param[2] != 0 or param[3] != limit \
            or param[4] != 1 or param[5] != 1 or param[6] != 1:

        print("correct display image")
        print("contrast value : %f" % param[0])
        print("brightness value : %f" % param[1])
        print("pente : %f" % (1. / ((param[3] - param[2]) / limit)))
        new_stack_image = np.float32(new_stack_image)
        if param[4] != 1 or param[5] != 1 or param[6] != 1:
            if mode == "rgb":
                print("R contrast value : %f" % param[4])
                print("G contrast value : %f" % param[5])
                print("B contrast value : %f" % param[6])
                new_stack_image[:, :, 0] = new_stack_image[:, :, 0] * param[6]
                new_stack_image[:, :, 1] = new_stack_image[:, :, 1] * param[5]
                new_stack_image[:, :, 2] = new_stack_image[:, :, 2] * param[4]

        if param[2] != 0 or param[3] != limit:
            new_stack_image = np.where(new_stack_image < param[3], new_stack_image, param[3])
            new_stack_image = np.where(new_stack_image > param[2], new_stack_image, param[2])
            new_stack_image = new_stack_image * (1. / ((param[3] - param[2]) / limit))

        if param[0] != 1 or param[1] != 0:
            new_stack_image = new_stack_image * param[0] + param[1]

        new_stack_image = np.where(new_stack_image < limit, new_stack_image, limit)
        new_stack_image = np.where(new_stack_image > 0, new_stack_image, 0)
        if im_type == "uint16":
            new_stack_image = np.uint16(new_stack_image)
        elif im_type == "uint8":
            new_stack_image = np.uint8(new_stack_image)

    cv2.imwrite(work_path + "/" + name_of_tiff_image, new_stack_image)
    print("TIFF image create : %s" % work_path + "/" + name_of_tiff_image)

    return 1


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
        limit = 2. ** 8 - 1
    elif im_type == 'uint16':
        limit = 2. ** 16 - 1
    else:
        raise ValueError("fit format not support")

    return limit, im_type


def create_first_ref_im(work_path, im_path, save_im=False, param=[]):

    # test image format ".fit" or ".fits" or other
    if im_path.rfind(".fit") != -1:
        if im_path[im_path.rfind(".fit"):] == ".fit":
            extension = ".fit"
        elif im_path[im_path.rfind(".fit"):] == ".fits":
            extension = ".fits"
        raw_im = False
    else:
        extension = im_path[im_path.rfind("."):]
        raw_im = True

    # remove extension
    name = im_path.replace(extension, '')
    # remove path
    name = name[name.rfind("/") + 1:]

    if not raw_im:
        # open ref image
        ref_fit = fits.open(im_path)
        ref = ref_fit[0].data
        # save header
        ref_header = ref_fit[0].header
        ref_fit.close()
        limit, im_type = test_utype(ref)
        # test rgb or gray
        ref, mode = test_and_debayer_to_rgb(ref_header, ref)
    else:
        print("convert DSLR image ...")
        ref = rawpy.imread(im_path).postprocess(gamma=(1, 1), no_auto_bright=True, output_bps=16)
        mode = "rgb"
        extension = ".fits"
        limit = 2. ** 16 - 1
        ref = np.rollaxis(ref, 2, 0)

    # red = fits.PrimaryHDU(data=ref)
    # red.writeto(work_path + "/" + ref_name)
    # red.writeto(work_path + "/" + "first_" + ref_name)

    save_tiff(work_path, ref, mode=mode, param=param)

    if save_im:
        # save stack image in fit
        red = fits.PrimaryHDU(data=ref)
        red.writeto(work_path + "/" + "stack_image_" + name + extension)
        # red.close()
        del red

    return ref, limit, mode


def stack_live(ref, first_ref, work_path, new_image_path, counter, save_im=False, align=True,
               stack_methode="Sum", param=[]):
    # test image format ".fit" or ".fits" or other
    if new_image_path.rfind(".fit") != -1:
        if new_image_path[new_image_path.rfind(".fit"):] == ".fit":
            extension = ".fit"
        elif new_image_path[new_image_path.rfind(".fit"):] == ".fits":
            extension = ".fits"
        raw_im = False
    else:
        extension = new_image_path[new_image_path.rfind("."):]
        raw_im = True
    # remove extension
    name = new_image_path.replace(extension, '')
    # remove path
    name = name[name.rfind("/") + 1:]

    if not raw_im:
        # open new image
        new_fit = fits.open(new_image_path)
        new = new_fit[0].data
        # save header
        new_header = new_fit[0].header
        new_fit.close()
        # test data type
        im_limit, im_type = test_utype(new)
        # test rgb or gray
        new, im_mode = test_and_debayer_to_rgb(new_header, new)
    else:
        print("convert DSLR image ...")
        new = rawpy.imread(new_image_path).postprocess(gamma=(1, 1), no_auto_bright=True, output_bps=16)
        im_mode = "rgb"
        extension = ".fits"
        im_limit = 2. ** 16 - 1
        im_type = "uint16"
        new = np.rollaxis(new, 2, 0)

    # open ref image
    # ref_fit = fits.open(work_path + "/" + ref_name)
    # ref = ref_fit[0].data
    # ref_fit.close()
    # test data type
    # ref_limit, ref_type = test_utype(ref)

    # if align:
    #    # open first ref image (for align)
    #    first_ref_fit = fits.open(work_path + "/" + "first_" + ref_name)
    #    first_ref = first_ref_fit[0].data
    #    first_ref_fit.close()

    # choix rgb ou gray scale
    print("alignement and stacking...")
    if im_mode == "rgb":
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
        del new

    elif im_mode == "gray":
        if align:
            # alignement
            p, __ = al.find_transform(new, first_ref)
            align_image = al.apply_transform(p, new, ref)
            del p
            del new
        else:
            align_image = new
            del new

        # stacking
        if stack_methode == "Sum":
            stack = np.float32(align_image) + np.float32(ref)
        elif stack_methode == "Mean":
            stack = ((counter - 1) * np.float32(ref) + np.float32(align_image)) / counter
        else:
            raise ValueError("Stack method is not support")

        if im_type == 'uint8':
            stack_image = np.uint8(np.where(stack < 2 ** 8 - 1, stack, 2 ** 8 - 1))
        elif im_type == 'uint16':
            stack_image = np.uint16(np.where(stack < 2 ** 16 - 1, stack, 2 ** 16 - 1))

    else:
        raise ValueError("Mode not support")

    # save new stack ref image in fit
    # os.remove(work_path + "/" + ref_name)
    # red = fits.PrimaryHDU(data=stack_image)
    # red.writeto(work_path + "/" + ref_name)
    if save_im:
        # save stack image in fit
        red = fits.PrimaryHDU(data=stack_image)
        red.writeto(work_path + "/" + "stack_image_" + name + extension)
        # red.close()
        del red

    # save stack image in tiff (print image)
    os.remove(work_path + "/" + name_of_tiff_image)
    tiff_name_path = save_tiff(work_path, np.array(stack_image), mode=im_mode, param=param)

    return np.array(stack_image)
