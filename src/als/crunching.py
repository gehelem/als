"""
A set of shared utilities for number crunching
"""
import logging

import numpy as np
from als.code_utilities import log
from als.model.base import Image

from als.model.data import HistogramContainer

_LOGGER = logging.getLogger(__name__)


@log
def compute_histograms_for_display(image, bin_count):
    """
    Compute histograms
    """
    container = HistogramContainer()

    if image.is_color():
        for channel in range(3):
            container.add_histogram(_compute_single_channel_histogram_for_display(image.data[:, :, channel], bin_count))
    else:
        container.add_histogram(_compute_single_channel_histogram_for_display(image.data, bin_count))

    container.global_maximum = max([histo.max() for histo in container.get_histograms()])

    return container


@log
def _compute_single_channel_histogram_for_display(channel_data, bin_count):

    histogram = np.histogram(channel_data, bin_count, range=(0, 2**16 - 1))[0]

    # we set extremity bins' values to 0 to prevent wrong display on clipped histograms
    histogram[0] = 0

    for current_bin in reversed(range(0, bin_count)):
        if histogram[current_bin] > 0:
            histogram[current_bin] = 0
            break

    return histogram


@log
def get_image_memory_size(image: Image):
    """
    compute memory footprint of a standardize image.

    each pixel needs 4 bytes as we normalize images data to np.float32

    So, image memory footmrpint = 4 bytes * image width * image height * image channels

    :param image: the image
    :type image: Image

    :return: memory footprint of image in bytes
    :rtype: int
    """
    if image.is_color():
        (a, b, c) = image.data.shape
        return 4 * a * b * c

    (a, b) = image.data.shape
    return 4 * a * b