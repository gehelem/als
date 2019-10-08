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
from PyQt5.QtCore import QThread, pyqtSignal
from skimage.transform import SimilarityTransform

from als.code_utilities import log, Timer
from als.model import Image, SignalingQueue, STORE, STACKING_MODE_SUM, STACKING_MODE_MEAN

_LOGGER = logging.getLogger(__name__)


class Stacker(QThread):

    stack_size_changed_signal = pyqtSignal(int)

    """
    Responsible of image stacking : alignment and registration
    """
    @log
    def __init__(self, stack_queue):
        QThread.__init__(self)
        self._stack_queue: SignalingQueue = stack_queue
        self._counter: int = 0
        self._stop_asked: bool = False
        self._reference: Image = None

    @log
    def reset(self):
        self._counter = 0
        self._reference = None
        self.stack_size_changed_signal.emit(self.size)

    @log
    def _store_result_image(self, image: Image):
        # TODO : publish to datastore
        self._reference = image
        self._counter += 1
        self.stack_size_changed_signal.emit(self.size)

    @property
    def size(self):
        return self._counter

    @log
    def run(self):
        while not self._stop_asked:

            if self._stack_queue.qsize() > 0:

                image = self._stack_queue.get()

                _LOGGER.info(f"Start stacking image : {image.origin}")

                with Timer() as stacking_timer:
                    if self.size == 0:
                        self._store_result_image(image)
                    else:
                        if STORE.align_before_stacking:
                            image = self._align_image(image)
                        image = self._register_image(image)
                        self._store_result_image(image)

                _LOGGER.info(f"Finished stacking image : {image.origin} in "
                             f"{stacking_timer.elapsed_in_milli_as_str} ms")

            self.msleep(20)

    @log
    def _align_image(self, image):

        with Timer() as transformation_find_timer:
            transformation = self._compute_transformation(image)
        _LOGGER.info(f"Computed transformation for alignment of {image.origin} in "
                     f"{transformation_find_timer.elapsed_in_milli_as_str} ms")

        with Timer() as transformation_apply_timer:
            image = self._apply_transformation(image, transformation)
        _LOGGER.info(f"Applied transformation for alignment of {image.origin} in "
                     f"{transformation_apply_timer.elapsed_in_milli_as_str} ms")

        return image


    @log
    def _apply_transformation(self, image: Image, transformation: SimilarityTransform):

        if image.is_color():
            _LOGGER.debug(f"Aligning color image...")
            for channel in range(3):
                _LOGGER.debug(f"Aligning channel {['Red', 'Green', 'Blue'][channel]}")
                image.data[channel] = al.apply_transform(
                    transformation,
                    image.data[channel],
                    self._reference.data[channel])
            _LOGGER.debug(f"Aligning color image : DONE")
        else:
            _LOGGER.debug(f"Aligning b&w image...")
            image.data = al.apply_transform(
                transformation,
                image.data,
                self._reference.data)
            _LOGGER.debug(f"Aligning b&w image : DONE")

        return image

    @log
    def _compute_transformation(self, image: Image):

        # pick green channel for star matching on color images

        if image.is_color():
            (new_field, reference_field) = (image.data[1], self._reference.data[1])
        else:
            (new_field, reference_field) = (image.data, self._reference.data)

        transformation, __ = al.find_transform(new_field, reference_field)

        return transformation

    @log
    def _register_image(self, image):

        with Timer() as registering_timer:

            stacking_mode = STORE.stacking_mode

            if stacking_mode == STACKING_MODE_SUM:
                image.data = image.data + self._reference.data
            elif stacking_mode == STACKING_MODE_MEAN:
                image.data = (self.size * self._reference.data + image.data) / (self.size + 1)
            else:
                _LOGGER.warning(f"Unsupported stacking mode : {stacking_mode}. {image.origin} is SKIPPED")

        _LOGGER.info(f"Done {stacking_mode}-registering {image.origin} in "
                     f"{registering_timer.elapsed_in_milli_as_str} ms")

        return image

    @log
    def stop(self):
        self._stop_asked = True
        self.wait()
        _LOGGER.info("Stacker stopped")
