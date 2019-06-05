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
import time
import astroalign as al
import numpy as np
from astropy.io import fits
from tqdm import tqdm
import rawpy
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def test_and_debayer_to_rgb(header, image, log):
    """
    Function for test fit image type : B&W, RGB or RGB no debayer
    For RGB no debayer this fonction debayer image

    :param header: header of fit image
    :param image: fit imae
    :return: image and process mode ("gray" or "rgb")
    """

    # test image Type
    # use fit header for separate B&W to no debayer image
    if len(image.shape) == 2 and not ("BAYERPAT" in header):
        #log.append(_("B&W mode"))
        new_mode = "gray"
    elif len(image.shape) == 3:
        #log.append(_("RGB mode"))
        new_mode = "rgb"
    elif len(image.shape) == 2 and "BAYERPAT" in header:
        #log.append(_("debayer..."))
        debay = header["BAYERPAT"]

        # test bayer type and debayer
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
            log.append(_("unknown bayer pattern"))
            raise ValueError(_("unknown bayer pattern"))

        # convert cv2 order to classic order:
        image = np.rollaxis(rgb_image, 2, 0)
        new_mode = "rgb"
    else:
        raise ValueError(_("invalid fit format"))

    #log.append(new_mode)
    return image, new_mode


def test_utype(image,log):
    """
    Test Image types (uint8 or uint16)

    :param image: image, numpy array
    :return: limit and type of image
    """
    # search type (uint8 or uint16)
    im_type = image.dtype.name
    if im_type == 'uint8':
        limit = 2. ** 8 - 1
    elif im_type == 'uint16':
        limit = 2. ** 16 - 1
    else:
        log.append(_("invalid fit format"))
        raise ValueError(_("invalid fit format"))
    #log.append(im_type)
    return limit, im_type