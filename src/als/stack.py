"""
Provides image stacking features
"""
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
import logging

import astroalign as al
import cv2
import numpy as np
import rawpy
from PyQt5.QtCore import QThread, pyqtSignal
from astropy.io import fits
from tqdm import tqdm

# classic order = 3xMxN
# cv2 order = MxNx3
# uint = unsignet int ( 0 to ...)
from als.code_utilities import log
from als.model import Image

_LOGGER = logging.getLogger(__name__)


class Stacker(QThread):

    stack_size_changed_signal = pyqtSignal(int)

    """
    Responsible of image stacking, that is alignment and registration
    """
    @log
    def __init__(self, stack_queue):
        QThread.__init__(self)
        self._stack_queue = stack_queue
        self._images = list()
        self._stop_asked = False

    @log
    def reset(self):
        self._images.clear()
        self.stack_size_changed_signal.emit(self.size)

    @log
    def _add_image(self, image: Image):
        self._images.append(image)
        self.stack_size_changed_signal.emit(self.size)

    @property
    def size(self):
        return len(self._images)

    @log
    def run(self):
        while not self._stop_asked:
            if self._stack_queue.qsize() > 0:
                self._add_image(self._stack_queue.get())
                last_image = self._images[-1]

                _LOGGER.info(f"Start stacking image : {last_image.origin}")

                if self.size > 1:
                    self._align_image(last_image)
                    self._register_image(last_image)

            # TODO : publish result

            self.msleep(20)

    @log
    def _align_image(self, image):
        # TODO
        pass

    @log
    def _register_image(self, image):
        # TODO
        pass

    @log
    def stop(self):
        self._stop_asked = True
        self.wait()
        _LOGGER.info("Stacker stopped")


@log
def test_and_debayer_to_rgb(header, image):
    """
    Function for test fit image type : B&W, RGB or RGB no debayer
    For RGB no debayer this fonction debayer image

    :param header: header of fit image
    :param image: fit imae
    :return: image and process mode ("gray" or "rgb")
    """

    # test image Type
    # use fit header for separate B&W to no debayer image
    if len(image.shape) == 2 and not "BAYERPAT" in header:
        _LOGGER.info("B&W mode...")
        new_mode = "gray"
    elif len(image.shape) == 3:
        _LOGGER.info("RGB mode...")
        new_mode = "rgb"
    elif len(image.shape) == 2 and "BAYERPAT" in header:
        _LOGGER.info("debayering...")
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
            raise ValueError("this debayer option not support")

        # convert cv2 order to classic order:
        image = np.rollaxis(rgb_image, 2, 0)
        new_mode = "rgb"
    else:
        raise ValueError("fit format not support")

    return image, new_mode


@log
def get_limit_and_utype(image):
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
        raise ValueError("fit format not support")

    return limit, im_type


@log
def create_first_ref_im(im_path):
    """
    function for process first image (need remove and add option or read counter)

    :param im_path: string, path of process image
    :return: image: np.array 3xMxN or MxN
             im_limit: int, bit limit (255 or 65535)
             im_mode: string, mode : "rgb" or "gray"
    """

    # test image format ".fit" or ".fits" or other
    if im_path.rfind(".fit") != -1:
        if im_path[im_path.rfind(".fit"):] == ".fit":
            extension = ".fit"
        elif im_path[im_path.rfind(".fit"):] == ".fits":
            extension = ".fits"
        raw_im = False
    else:
        # Other format = raw camera format (cr2, ...)
        extension = im_path[im_path.rfind("."):]
        raw_im = True

    # remove extension of path
    name = im_path.replace(extension, '')
    # remove path, juste save image name
    name = name[name.rfind("/") + 1:]

    if not raw_im:
        # open ref fit image
        new_fit = fits.open(im_path)
        new = new_fit[0].data
        # save fit header
        new_header = new_fit[0].header
        new_fit.close()
        # test image type
        im_limit, _ = get_limit_and_utype(new)
        # test rgb or gray or no debayer
        new, im_mode = test_and_debayer_to_rgb(new_header, new)
    else:
        _LOGGER.info("convert DSLR image ...")
        # convert camera raw to numpy array
        new = rawpy.imread(im_path).postprocess(gamma=(1, 1), no_auto_bright=True, output_bps=16, user_flip=0)
        im_mode = "rgb"
        extension = ".fits"
        im_limit = 2. ** 16 - 1
        # convert cv2 order to classic order
        new = np.rollaxis(new, 2, 0)

    image = new
    del new

    return image, im_limit, im_mode


@log
def stack_live(im_path, counter, ref=[], first_ref=[], align=True,
               stack_methode="Sum"):
    """
    function for process image, align and stack

    :param im_path: string, path of process image
    :param ref: np.array, stack image (no for first image)
    :param first_ref: np.array, first image process, ref for alignement (no for first image)
    :param counter: int, number of image stacked
    :param align: bool, option for align image or not
    :param stack_methode: string, stack methode ("sum" or "mean")
    :return: image: np.array 3xMxN or MxN
             im_limit: int, bit limit (255 or 65535)
             im_mode: string, mode : "rgb" or "gray"

    TODO: Add dark possibility
    """

    # test image format ".fit" or ".fits" or other
    if im_path.rfind(".fit") != -1:
        if im_path[im_path.rfind(".fit"):] == ".fit":
            extension = ".fit"
        elif im_path[im_path.rfind(".fit"):] == ".fits":
            extension = ".fits"
        raw_im = False
    else:
        # Other format = raw camera format (cr2, ...)
        extension = im_path[im_path.rfind("."):]
        raw_im = True
    # remove extension of path
    name = im_path.replace(extension, '')
    # remove path, juste save image name
    name = name[name.rfind("/") + 1:]

    if not raw_im:
        # open new image
        new_fit = fits.open(im_path)
        new = new_fit[0].data
        # save header
        new_header = new_fit[0].header
        new_fit.close()
        # test data type
        im_limit, im_type = get_limit_and_utype(new)
        # test rgb or gray
        new, im_mode = test_and_debayer_to_rgb(new_header, new)
    else:
        _LOGGER.info("convert DSLR image ...")
        new = rawpy.imread(im_path).postprocess(gamma=(1, 1), no_auto_bright=True, output_bps=16, user_flip=0)
        im_mode = "rgb"
        extension = ".fits"
        im_limit = 2. ** 16 - 1
        im_type = "uint16"
        new = np.rollaxis(new, 2, 0)

    # ____________________________________
    # specific part for no first image
    # choix rgb ou gray scale
    _LOGGER.info("alignement and stacking...")

    # choix du mode (rgb or B&W)
    if im_mode == "rgb":
        if align:
            # alignement with green :
            transformation, __ = al.find_transform(new[1], first_ref[1])

        # stacking
        stack_image = []
        for j in tqdm(range(3)):
            if align:
                # align all color :
                align_image = al.apply_transform(transformation, new[j], ref[j])

            else:
                align_image = new[j]

            # chose stack methode
            # need convert to float32 for excess value
            if stack_methode == "Sum":
                stack = np.float32(align_image) + np.float32(ref[j])
            elif stack_methode == "Mean":
                stack = ((counter - 1) * np.float32(ref[j]) + np.float32(align_image)) / counter
            else:
                raise ValueError("Stack method is not support")

            # filter excess value > limit
            if im_type == 'uint8':
                stack_image.append(np.uint8(np.where(stack < 2 ** 8 - 1, stack, 2 ** 8 - 1)))
            elif im_type == 'uint16':
                stack_image.append(np.uint16(np.where(stack < 2 ** 16 - 1, stack, 2 ** 16 - 1)))
        del stack
        del new

    elif im_mode == "gray":
        if align:
            # alignement
            transformation, __ = al.find_transform(new, first_ref)
            align_image = al.apply_transform(transformation, new, ref)
        else:
            align_image = new

        del new

        # chose stack methode
        # need convert to float32 for excess value
        if stack_methode == "Sum":
            stack = np.float32(align_image) + np.float32(ref)
        elif stack_methode == "Mean":
            stack = ((counter - 1) * np.float32(ref) + np.float32(align_image)) / counter
        else:
            raise ValueError("Stack method is not support")

        # filter excess value > limit
        if im_type == 'uint8':
            stack_image = np.uint8(np.where(stack < 2 ** 8 - 1, stack, 2 ** 8 - 1))
        elif im_type == 'uint16':
            stack_image = np.uint16(np.where(stack < 2 ** 16 - 1, stack, 2 ** 16 - 1))
        del stack

    else:
        raise ValueError("Mode not support")

    image = np.array(stack_image)

    return image, im_limit, im_mode
