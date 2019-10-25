"""
A set of shared utilities for number crunching
"""
import logging

import numpy as np
from als.code_utilities import log

from als.model.data import HistogramContainer

_LOGGER = logging.getLogger(__name__)


@log
def compute_histograms_for_display(image, bin_count):
    """
    Compute histograms
    """
    container = HistogramContainer()
    temp_image = image.clone()

    if temp_image.is_color():
        temp_image.set_color_axis_as(0)
        for channel in range(3):
            container.add_histogram(np.histogram(temp_image.data[channel], bin_count)[0])
    else:
        container.add_histogram(np.histogram(temp_image.data, bin_count)[0])

    # We first need to find the global maximum among our histograms
    #
    # We remove first and last item of a copy of each histogram before getting its max value
    # so we don't end up with a vertically squashed display if histogram is clipping on black or white
    global_maximum = max([tweaked_histogram.max() for tweaked_histogram in [
        np.delete(histogram, [0, bin_count - 1]) for histogram in container.get_histograms()
    ]])

    if global_maximum == 0:
        # In some very rare cases, i.e. playing with images of pure single primary colors,
        # the global maximum will be 0 after removing the 2 extreme bins of the original histograms
        #
        # As only Chuck Norris can divide by zero, we replace this 0 with the global maximum
        # among our *original* histograms
        global_maximum = max([original_histo.max() for original_histo in container.get_histograms()])

    container.global_maximum = global_maximum

    return container
