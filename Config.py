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
"""
Provides application defaults and high level access to user settings
"""
import logging
import os
import sys
from configparser import ConfigParser

# config file path. We use the pseudo-standard hidden file in user's home
_CONFIG_FILE_PATH = os.path.expanduser("~/.als.cfg")

# keys used to retrieve config values
_SCAN_FOLDER_PATH = "scan_folder_path"
_WORK_FOLDER_PATH = "work_folder_path"
_DARK_PATH = "dark_path"
_LOG_LEVEL = "log_level"

# keys used to describe logging level
_LOG_LEVEL_DEBUG = "DEBUG"
_LOG_LEVEL_INFO = "INFO"
_LOG_LEVEL_WARNING = "WARNING"
_LOG_LEVEL_ERROR = "ERROR"
_LOG_LEVEL_CRITICAL = "CRITICAL"

# store of matches between human readable log levels and logging module constants
_LOG_LEVELS = {
    _LOG_LEVEL_DEBUG:       logging.DEBUG,
    _LOG_LEVEL_INFO:        logging.INFO,
    _LOG_LEVEL_WARNING:     logging.WARNING,
    _LOG_LEVEL_ERROR:       logging.ERROR,
    _LOG_LEVEL_CRITICAL:    logging.CRITICAL,
}

# application default values
_DEFAULTS = {
    _SCAN_FOLDER_PATH:    os.path.expanduser("~/als/scan"),
    _WORK_FOLDER_PATH:    os.path.expanduser("~/als/work"),
    _DARK_PATH:           os.path.expanduser("~/als/sample/dark.fits"),
    _LOG_LEVEL:           "INFO",
}
_MAIN_SECTION_NAME = "main"

_config_parser = ConfigParser()


def get_work_folder_path():
    return _get(_WORK_FOLDER_PATH)


def set_work_folder_path(path):
    _set(_WORK_FOLDER_PATH, path)


def get_scan_folder_path():
    return _get(_SCAN_FOLDER_PATH)


def set_scan_folder_path(path):
    _set(_SCAN_FOLDER_PATH, path)


def get_dark_path():
    return _get(_DARK_PATH)


def set_dark_path(path):
    _set(_DARK_PATH, path)


def save():
    with open(_CONFIG_FILE_PATH, "w") as config_file:
        _config_parser.write(config_file)


def _get(key):
    # we rely on the fallback machanism to get our predefined defaults
    # if no user config is found
    return _config_parser.get(_MAIN_SECTION_NAME, key, fallback=_DEFAULTS[key])


def _set(key, value):
    # we only store the value if it differs from default or already stored one
    if value != _get(key):
        _config_parser.set(_MAIN_SECTION_NAME, key, value)


# ConfigParser.read won't raise an exception if read fails
# so if app starts and no user settings file exists, we simply
# get an "empty" config
_config_parser.read(_CONFIG_FILE_PATH)

# init logging system
logging.basicConfig(level=_LOG_LEVELS[_get(_LOG_LEVEL)],
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    stream=sys.stdout)
_logger = logging.getLogger(__name__)

# add our main section if not already present (i.e. previous read failed)
if not _config_parser.has_section(_MAIN_SECTION_NAME):
    _logger.debug('adding main section to config')
    _config_parser.add_section(_MAIN_SECTION_NAME)

# cleanup unused options
for option in _config_parser.options(_MAIN_SECTION_NAME):
    if option not in _DEFAULTS.keys():
        _logger.debug(f"Removed obsolete config option : '{option}'")
        _config_parser.remove_option(_MAIN_SECTION_NAME, option)
