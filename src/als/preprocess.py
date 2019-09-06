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


# Numerical stuff
import logging

import cv2
# Wavelet stuff
import dtcwt
import numpy as np
from pywi.processing.transform import starlet

# Local stuff
from als import stack as stk
from als.code_utilities import log

NAME_OF_TIFF_IMAGE = "stack_image.tiff"
NAME_OF_JPEG_IMAGE = "stack_image.jpg"
NAME_OF_PNG_IMAGE = "stack_image.png"

_logger = logging.getLogger(__name__)


@log
def wavelets(image, wavelets_type, wavelets_use_luminance, parameters):
    """
    Module allowing to play with coefficients of a redudant frame from the
    wavelet family.
    A ratio is applied to each level
    :param image:      input image
    :param wavelets_type: either 'deep sky' or 'planetary' gives the family
                            of wavelets to be used for processing
    :param parameters: ratio to be applied for each level of the wavelet
                        decomposition
    :return:           denoised/enhanced image
    """

    @log
    def apply_dt_wavelets(img, param):
        # pylint: disable=E1101
        # Compute 5 levels of dtcwt with the antonini/qshift settings
        input_shape = img.shape
        transform = dtcwt.Transform2d(biort='antonini', qshift='qshift_06')
        t = transform.forward(img, nlevels=len(param))

        for level, ratio in param.items():
            data = t.highpasses[level - 1]
            if ratio < 1:
                norm = np.absolute(data)
                # 1 keeps 100% of the coefficients, 0 keeps 0% of the coeff
                thresh = np.percentile(norm, 100 * (1 - ratio))
                # Proximity operator for L1,2 norm
                data[:, :, :] = np.where(norm < thresh, 0,
                                         (norm - thresh) * np.exp(1j * np.angle(data)))
            else:
                # Just applying gain for this level
                data *= ratio
        ret = transform.inverse(t)
        # in some cases dtcwt does reshape the image for performance purpose
        return ret[:input_shape[0], :input_shape[1]]

    @log
    def apply_star_wavelets(img, param):
        # Compute 5 levels of starlets
        t = starlet.wavelet_transform(img, number_of_scales=len(param))

        for level, ratio in param.items():
            data = t[level - 1]
            if ratio < 1:
                norm = np.absolute(data)
                # 1 keeps 100% of the coefficients, 0 keeps 0% of the coeff
                thresh = np.percentile(norm, 100 * (1 - ratio))
                # Proximity operator for L1 norm
                data[:, :] = np.where(norm < thresh, 0,
                                      (norm - thresh) * np.sign(data))
            else:
                # Just applying gain for this level
                data *= ratio
        return starlet.inverse_wavelet_transform(t)

    # Choose in between members of a catalog
    wavelet_db = {'deep sky': apply_star_wavelets,
                  'planetary': apply_dt_wavelets}

    # in case of rgb image with 3 channels
    if len(image.shape) > 2:
        # either process wvlts only on the value channel of hsv space
        if wavelets_use_luminance:
            hsv_img = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            hsv_img[:, :, 2] = wavelet_db[wavelets_type](hsv_img[:, :, 2], parameters)
            image = cv2.cvtColor(hsv_img, cv2.COLOR_HSV2RGB)
        # or compute 3 times the wvlt process. More expensive, but usually this
        # yields better results
        else:
            # apply wvlt to all channels if available
            for channel_index in range(image.shape[2]):
                image[:, :, channel_index] = wavelet_db[wavelets_type](
                    image[:, :, channel_index], parameters)
    else:
        image = wavelet_db[wavelets_type](image, parameters)
    return image


@log
def scnr(rgb_image, im_limit, rgb_type="RGB", scnr_type="ne_m", amount=0.5):
    """
    Function for reduce green noise on image
    SCNR Average Neutral Protection

    :param rgb_image: Numpy array (float32), size 3xMxN
    :param im_type: string, uint16 or uint8
    :param im_limit: int, value limit, 255 or 65535
    :param rgb_type: RGB or BGR
    :param scnr_type: string, correction type : ne_m, ne_max, ma_ad or ma_max
    :param amount: float, 0 to 1, param for ma_ad and ma_max
    :return: image corrected (np.array(float32))

    """

    # Swap blue and red for different mode :
    if rgb_type == "RGB":
        red = 0
        blue = 2
    elif rgb_type == "BGR":
        red = 2
        blue = 0

    # process image
    if scnr_type == "Av Neutral":
        m = (rgb_image[red] + rgb_image[blue]) * 0.5
        compare = rgb_image[1] < m
        rgb_image[1] = compare * rgb_image[1] + np.invert(compare) * m

    elif scnr_type == "Max Neutral":
        compare = rgb_image[red] > rgb_image[blue]
        m = compare * rgb_image[red] + np.invert(compare) * rgb_image[blue]
        compare = rgb_image[1] < m
        rgb_image[1] = compare * rgb_image[1] + np.invert(compare) * m

    elif scnr_type == "Add Mask":
        rgb_image = rgb_image / im_limit
        unity_m = np.ones((rgb_image[1].shape[0], rgb_image[1].shape[1]))
        compare = unity_m < (rgb_image[blue] + rgb_image[red])
        m = compare * unity_m + np.invert(compare) * (rgb_image[blue] + rgb_image[red])
        rgb_image[1] = rgb_image[1] * (1 - amount) * (1 - m) + m * rgb_image[1]
        rgb_image = rgb_image * im_limit

    elif scnr_type == "Max Mask":
        rgb_image = rgb_image / im_limit
        compare = rgb_image[red] > rgb_image[blue]
        m = compare * rgb_image[red] + np.invert(compare) * rgb_image[blue]
        rgb_image[1] = rgb_image[1] * (1 - amount) * (1 - m) + m * rgb_image[1]
        rgb_image = rgb_image * im_limit

    return rgb_image


@log
def save_tiff(work_path, stack_image, log_ui, mode="rgb", scnr_on=False,
              wavelets_on=False, wavelets_type='deep sky',
              wavelets_use_luminance=False, param=[], image_type="tiff"):
    """
    Fonction for create print image and post process this image

    :param work_path: string, path for work folder
    :param stack_image: np.array(uintX), Image, 3xMxN or MxN
    :param log_ui: QT log for print text in QT GUI
    :param mode: image mode ("rgb" or "gray")
    :param scnr_on: bool, activate scnr correction
    :param wavelets_on: bool, activate wavelet filtering
    :param param: post process param
    :param image_type: "tiff", "no" and "jpeg"
    :return: no return

    """

    # change action for mode :
    if mode == "rgb":
        log_ui.append(_("Save New Image in RGB..."))
        # convert clissic classic order to cv2 order
        new_stack_image = np.rollaxis(stack_image, 0, 3)
        # convert RGB color order to BGR
        new_stack_image = cv2.cvtColor(new_stack_image, cv2.COLOR_RGB2BGR)
    elif mode == "gray":
        log_ui.append(_("Save New Image in B&W..."))
        new_stack_image = stack_image

    # read image number type
    limit, im_type = stk.test_utype(new_stack_image)

    # if no have change, no process
    if param[0] != 1 or param[1] != 0 or param[2] != 0 or param[3] != limit \
            or param[4] != 1 or param[5] != 1 or param[6] != 1 or any([v != 1 for _, v in param[9].items()]):

        # print param value for post process
        log_ui.append(_("Post-Process New Image..."))
        log_ui.append(_("correct display image"))
        log_ui.append(_("contrast value :") + " %f" % param[0])
        log_ui.append(_("brightness value :") + "%f" % param[1])
        log_ui.append(_("pente : ") + "%f" % (1. / ((param[3] - param[2]) / limit)))

        # need convert to float32 for excess value
        new_stack_image = np.float32(new_stack_image)

        if scnr_on:
            log_ui.append(_("apply SCNR"))
            log_ui.append(_("SCNR type") + "%s" % param[7])
            new_stack_image = scnr(new_stack_image, limit, rgb_type="BGR", scnr_type=param[7], amount=param[8])

        if wavelets_on:
            log_ui.append("apply Wavelets")
            log_ui.append("Wavelets parameters {}".format(param[9]))
            new_stack_image = wavelets(new_stack_image,
                                       wavelets_type=wavelets_type,
                                       wavelets_use_luminance=wavelets_use_luminance,
                                       parameters=param[9])

        # if change in RGB value
        if param[4] != 1 or param[5] != 1 or param[6] != 1:
            if mode == "rgb":
                # invert Red and Blue for cv2
                # print RGB contrast value
                log_ui.append(_("R contrast value : ") + "%f" % param[4])
                log_ui.append(_("G contrast value : ") + "%f" % param[5])
                log_ui.append(_("B contrast value : ") + "%f" % param[6])

                # multiply by RGB factor
                new_stack_image[:, :, 0] = new_stack_image[:, :, 0] * param[6]
                new_stack_image[:, :, 1] = new_stack_image[:, :, 1] * param[5]
                new_stack_image[:, :, 2] = new_stack_image[:, :, 2] * param[4]

        # if change in limit value
        if param[2] != 0 or param[3] != limit:
            # filter excess value with new limit
            new_stack_image = np.where(new_stack_image < param[3], new_stack_image, param[3])
            new_stack_image = np.where(new_stack_image > param[2], new_stack_image, param[2])
            # spread out the remaining values
            new_stack_image = new_stack_image * (1. / ((param[3] - param[2]) / limit))

        # if change in contrast/brightness value
        if param[0] != 1 or param[1] != 0:
            # new_image = image * contrast + brightness
            new_stack_image = new_stack_image * param[0] + param[1]

        # filter excess value > limit
        new_stack_image = np.where(new_stack_image < limit, new_stack_image, limit)
        new_stack_image = np.where(new_stack_image > 0, new_stack_image, 0)

        # reconvert in uintX format
        if im_type == "uint16":
            new_stack_image = np.uint16(new_stack_image)
        elif im_type == "uint8":
            new_stack_image = np.uint8(new_stack_image)

    # use cv2 fonction for save print image in tiff format
    if image_type == "tiff":
        cv2.imwrite(work_path + "/" + NAME_OF_TIFF_IMAGE, new_stack_image)
        _logger.info(_("TIFF image create :") + "%s" % work_path + "/" + NAME_OF_TIFF_IMAGE)
        new_stack_image = cv2.cvtColor(new_stack_image, cv2.COLOR_BGR2RGB)

    elif image_type == "png":
        print(new_stack_image.dtype)
        cv2.imwrite(work_path + "/" + NAME_OF_PNG_IMAGE, new_stack_image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        _logger.info(_("PNG image create :") + "%s" % work_path + "/" + NAME_OF_PNG_IMAGE)
        new_stack_image = cv2.cvtColor(new_stack_image, cv2.COLOR_BGR2RGB)

    elif image_type == "jpeg":
        # limitate to 8bit
        image_to_save = new_stack_image
        if "uint16" == image_to_save.dtype:
            bit_depth = 16
        else:
            bit_depth = 8

        if bit_depth > 8:
            image_to_save = (image_to_save / (((2**bit_depth)-1) / ((2**8)-1))).astype('uint8')

        cv2.imwrite(work_path + "/" + NAME_OF_JPEG_IMAGE, image_to_save, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        _logger.info(_("JPEG image create :") + "%s" % work_path + "/" + NAME_OF_JPEG_IMAGE)
        new_stack_image = cv2.cvtColor(new_stack_image, cv2.COLOR_BGR2RGB)
    elif image_type == "no":
        _logger.info(_("No image create, als use RAM"))
        new_stack_image = cv2.cvtColor(new_stack_image, cv2.COLOR_BGR2RGB)
    return new_stack_image
