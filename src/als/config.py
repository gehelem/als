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
from configparser import ConfigParser, DuplicateOptionError, ParsingError
from pathlib import Path

from als.code_utilities import AlsException
from als.model.data import IMAGE_SAVE_TYPE_JPEG, DYNAMIC_DATA

_CONFIG_FILE_PATH = os.path.expanduser("~/.als.cfg")

# keys used to retrieve config values
_SCAN_FOLDER_PATH = "scan_folder_path"
_WORK_FOLDER_PATH = "work_folder_path"
_WWW_FOLDER_PATH = "web_folder_path"
_WWW_DEDICATED_FOLDER = "www_dedicated_folder"
_LOG_LEVEL = "log_level"
_WWW_SERVER_PORT = "www_server_port"
_WINDOW_GEOMETRY = "window_geometry"
_IMAGE_SAVE_FORMAT = "image_save_format"
_FULL_SCREEN = "full_screen"
_WWW_REFRESH_PERIOD = "web_refresh_period"
_MINIMUM_MATCH_COUNT = "alignment_minimum_match_count"
_USE_MASTER_DARK = "use_master_dark"
_MASTER_DARK_FILE_PATH = "master_dark_file_path"
_USE_HOT_PIXEL_REMOVER = "use_hot_pixel_remover"
_LANG = "lang"
_BAYER_PATTERN = "bayer_pattern"
_NIGHT_MODE = "night_mode"
_SAVE_ON_STOP = "save_on_stop"
_PROFILE = "profile"

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
    _SCAN_FOLDER_PATH:      os.path.expanduser("~/als/scan"),
    _WORK_FOLDER_PATH:      os.path.expanduser("~/als/work"),
    _WWW_FOLDER_PATH:       os.path.expanduser("~/als/work"),
    _WWW_DEDICATED_FOLDER:  0,
    _LOG_LEVEL:             _LOG_LEVEL_INFO,
    _WWW_SERVER_PORT:       "8000",
    _WINDOW_GEOMETRY:       "50,100,1400,900",
    _IMAGE_SAVE_FORMAT:     IMAGE_SAVE_TYPE_JPEG,
    _FULL_SCREEN:           0,
    _WWW_REFRESH_PERIOD:    5,
    _MINIMUM_MATCH_COUNT:   25,
    _USE_MASTER_DARK:       0,
    _MASTER_DARK_FILE_PATH: "",
    _USE_HOT_PIXEL_REMOVER: 0,
    _LANG:                  "sys",
    _BAYER_PATTERN:         "AUTO",
    _NIGHT_MODE:            0,
    _SAVE_ON_STOP:          0,
    _PROFILE:               0,
}
_MAIN_SECTION_NAME = "main"

# application constants

# module global data
_CONFIG_PARSER = ConfigParser()


class CouldNotSaveConfig(AlsException):
    """Raised when config could not be saved"""


def set_full_screen_active(full: bool):
    """
    Set full screen indicator

    :param full: should app be launched in fullscreen mode ?
    :type full: bool
    """

    _set(_FULL_SCREEN, "1" if full else "0")


def get_full_screen_active():
    """
    Get full screen indicator

    :return: True if app should be launched in fullscreen mode, False otherwise
    :rtype: bool
    """

    try:
        return int(_get(_FULL_SCREEN)) == 1
    except ValueError:
        return _DEFAULTS[_FULL_SCREEN]


def set_night_mode_active(night: bool):
    """
    Set night mode indicator

    :param night: should app be launched in night mode ?
    :type night: bool
    """

    _set(_NIGHT_MODE, "1" if night else "0")


def get_night_mode_active():
    """
    Get night mode indicator

    :return: True if app should be launched in night mode, False otherwise
    :rtype: bool
    """

    try:
        return int(_get(_NIGHT_MODE)) == 1
    except ValueError:
        return _DEFAULTS[_NIGHT_MODE]


def set_www_use_dedicated_folder(dedicated: bool):
    """
    Set www dedicated folder flag

    :param dedicated: must webserver use its own web folder
    :type dedicated: bool
    """

    _set(_WWW_DEDICATED_FOLDER, "1" if dedicated else "0")


def get_www_use_dedicated_folder():
    """
    Get www dedicated folder flag

    :return: True if webserver must use its own web folder
    :rtype: bool
    """

    try:
        return int(_get(_WWW_DEDICATED_FOLDER)) == 1
    except ValueError:
        return _DEFAULTS[_WWW_DEDICATED_FOLDER]


def set_hot_pixel_remover(hpr_on: bool):
    """
    Set 'use hot pixel remover' flag

    :param hpr_on: should we use hot pixel remover ?
    :type hpr_on: bool
    """

    _set(_USE_HOT_PIXEL_REMOVER, "1" if hpr_on else "0")


def get_hot_pixel_remover():
    """
    Get 'use hot pixel remover' flag

    :return: True if app should use hot pixel remover, False otherwise
    :rtype: bool
    """

    try:
        return int(_get(_USE_HOT_PIXEL_REMOVER)) == 1
    except ValueError:
        return int(_DEFAULTS[_USE_HOT_PIXEL_REMOVER]) == 1


def set_save_on_stop(save_on_stop: bool):
    """
    Set 'save on stop' flag

    :param save_on_stop: should we save on stop
    :type save_on_stop: bool
    """

    _set(_SAVE_ON_STOP, "1" if save_on_stop else "0")


def get_save_on_stop():
    """
    Get 'save on stop' flag

    :return: True if app should save on stop, False otherwise
    :rtype: bool
    """

    try:
        return int(_get(_SAVE_ON_STOP)) == 1
    except ValueError:
        return int(_DEFAULTS[_SAVE_ON_STOP]) == 1


def get_image_save_format():
    """
    Retrieves the configured image save format.

    :return: format code. Can be any value from :

      - IMAGE_SAVE_TIFF
      - IMAGE_SAVE_PNG
      - IMAGE_SAVE_JPEG

    :rtype: str
    """
    return _get(_IMAGE_SAVE_FORMAT)


def set_image_save_format(save_format):
    """
    Sets image save format.

    :param save_format: format code. Can be any value from :

      - IMAGE_SAVE_TIFF
      - IMAGE_SAVE_PNG
      - IMAGE_SAVE_JPEG

    :type save_format: str
    """
    _set(_IMAGE_SAVE_FORMAT, save_format)


def is_debug_log_on():
    """
    Checks if loglevel is DEBUG

    :return: True if loglevel is DEBUG, False otherwise
    """
    return _get(_LOG_LEVEL) == 'DEBUG'


def set_debug_log(debug_active):
    """
    Sets logldevel to debug if debug_active is True, otherwise set loglevel to info

    :param debug_active: set loglevel to debug
    :type debug_active: bool
    """
    if debug_active:
        _set(_LOG_LEVEL, _LOG_LEVEL_DEBUG)
    else:
        _set(_LOG_LEVEL, _LOG_LEVEL_INFO)


def get_profile():
    """
    Retrieves the configured profile.

    :return: The configured profile, or its default value if config entry
             is not parsable as an int.
    """
    try:
        return int(_get(_PROFILE))
    except ValueError:
        return _DEFAULTS[_PROFILE]


def set_profile(profile):
    """
    Sets profile.

    :param profile: the profile
    :type profile: int
    """
    _set(_PROFILE, profile)


def get_www_server_port_number():
    """
    Retrieves the configured web server port number.

    :return: The configured port number, or its default value if config entry
             is not parsable as an int.
    """
    try:
        return int(_get(_WWW_SERVER_PORT))
    except ValueError:
        return _DEFAULTS[_WWW_SERVER_PORT]


def set_www_server_port_number(port_number):
    """
    Sets server port number.

    :param port_number: the port number
    :type port_number: int
    """
    _set(_WWW_SERVER_PORT, port_number)


def get_www_server_refresh_period():
    """
    Retrieves the configured web server page refresh period.

    :return: The web server page refresh period, or its default value if config entry
             is not parsable as an int.
    :rtype: int
    """
    try:
        return int(_get(_WWW_REFRESH_PERIOD))
    except ValueError:
        return _DEFAULTS[_WWW_REFRESH_PERIOD]


def set_www_server_refresh_period(period):
    """
    Sets web server page refresh period.

    :param period: the period
    :type period: int
    """
    _set(_WWW_REFRESH_PERIOD, str(period))


def get_work_folder_path():
    """
    Retrieves work folder path.

    :return: the work folder path
    :rtype: str
    """
    return _get(_WORK_FOLDER_PATH)


def set_work_folder_path(path):
    """
    Sets the work folder path.

    :param path: the work folder path
    :type path: str
    """
    _set(_WORK_FOLDER_PATH, path)


def get_bayer_pattern():
    """
    Retrieves preferred bayer pattern

    :return: the preferred bayer pattern
    :rtype: str
    """
    return _get(_BAYER_PATTERN)


def set_bayer_pattern(pattern):
    """
    Sets the preferred bayer pattern

    :param pattern: the work folder path
    :type pattern: str
    """
    _set(_BAYER_PATTERN, pattern)


def get_lang():
    """
    Retrieves preferred language

    :return: the preferred language
    :rtype: str
    """
    return _get(_LANG)


def set_lang(lang):
    """
    Sets the preferred language

    :param lang: the preferred language
    :type lang: str
    """
    _set(_LANG, lang)


def get_web_folder_path():
    """
    Retrieves web folder path.

    :return: the web folder path
    :rtype: str
    """
    return _get(_WWW_FOLDER_PATH)


def set_web_folder_path(path):
    """
    Sets the web folder path.

    :param path: the web folder path
    :type path: str
    """
    _set(_WWW_FOLDER_PATH, path)


def get_scan_folder_path():
    """
    Retrieves scan folder path.

    :return: the scan folder path
    :rtype: str
    """
    return _get(_SCAN_FOLDER_PATH)


def set_scan_folder_path(path):
    """
    Sets the scan folder path.

    :param path: the scan folder path
    :type path: str
    """
    _set(_SCAN_FOLDER_PATH, path)


def get_minimum_match_count():
    """
    Retrieves alignment minimum stars value.

    :return: the minimum stars number for alignment
    :rtype: int
    """
    try:
        return int(_get(_MINIMUM_MATCH_COUNT))
    except ValueError:
        return _DEFAULTS[_MINIMUM_MATCH_COUNT]


def set_minimum_match_count(minimum_match_count):
    """
    Sets the alignment minimum stars value.

    :param minimum_match_count: the minimum stars number for alignment
    :type minimum_match_count: int
    """
    _set(_MINIMUM_MATCH_COUNT, str(minimum_match_count))


def set_use_master_dark(use_dark: bool):
    """
    Set use dark flag

    :param use_dark: Remove master dark from images ?
    :type use_dark: bool
    """

    _set(_USE_MASTER_DARK, "1" if use_dark else "0")


def get_use_master_dark():
    """
    Get use dark flag

    :return: True if dark should be used, False otherwise
    :rtype: bool
    """

    try:
        return _get(_USE_MASTER_DARK) == "1"
    except ValueError:
        return _DEFAULTS[_USE_MASTER_DARK]


def get_master_dark_file_path():
    """
    Retrieves the master dark file path.

    :return: the master dark file path
    :rtype: str
    """
    return _get(_MASTER_DARK_FILE_PATH)


def set_master_dark_file_path(path):
    """
    Sets the master dark file path.

    :param path: the master dark file path
    :type path: str
    """
    _set(_MASTER_DARK_FILE_PATH, path)


def get_window_geometry():
    """
    Retrieves main window geometry.

    :return: a tuple of 4 integers describing :

    - x coordinate of top left corner
    - y coordinate of top left corner
    - width of the window
    - height of the window
    """
    return tuple([int(value) for value in _get(_WINDOW_GEOMETRY).split(",")])


def set_window_geometry(geometry_tuple):
    """
    Sets main window geometry.

    :param geometry_tuple:
    :type geometry_tuple: tuple

    The geometry_tuple tuple must contain 4 integers describing :

    - x coordinate of top left corner
    - y coordinate of top left corner
    - width of the window
    - height of the window
    """
    _set(_WINDOW_GEOMETRY, ",".join([str(value) for value in geometry_tuple]))


def save():
    """
    Saves settings to disk.

    :except os_error: Saving could not be done
    """
    try:

        with open(_CONFIG_FILE_PATH, "w") as config_file:
            _CONFIG_PARSER.write(config_file)
        _get_logger().info("User configuration saved")

    except OSError as os_error:
        message = "Could not save settings"
        details = str(os_error)
        _get_logger().error(f"{message} : {details}")
        raise CouldNotSaveConfig(message, details)


def _get(key):
    """
    Retrieves the value of a specific config entry.

    :param key: the key identifying the config entry
    :type key: str

    :return: the value of the config entry identified by key, or it's default value if key is not found
    """
    # we rely on the fallback mechanism to get our predefined defaults
    # if no user config is found
    return _CONFIG_PARSER.get(_MAIN_SECTION_NAME, key, fallback=_DEFAULTS[key])


def _set(key, value):
    """
    Sets the value of a config entry identified by a key *only* when value differs from default or stored one

    :param key: config entry key
    :type key: str
    :param value: config entry value
    :type value: any
    """
    if value != _get(key):
        _CONFIG_PARSER.set(_MAIN_SECTION_NAME, key, value)


def setup():
    """
    Sets config and log systems up.
    """
    # ConfigParser.read won't raise an exception if read fails because of missing file
    # so if app starts and no user settings file exists, we simply
    # get an "empty" config
    #
    # if config file is invalid, we raise a ValueError with details

    DYNAMIC_DATA.is_first_run = not Path(_CONFIG_FILE_PATH).is_file()

    try:
        _CONFIG_PARSER.read(_CONFIG_FILE_PATH)
    except DuplicateOptionError as duplicate_error:
        raise ValueError(duplicate_error)
    except ParsingError as parsing_error:
        raise ValueError(parsing_error)
    _setup_logging()

    # add our main config section if not already present (i.e. previous read failed)
    if not _CONFIG_PARSER.has_section(_MAIN_SECTION_NAME):
        _get_logger().debug('adding main section to config')
        _CONFIG_PARSER.add_section(_MAIN_SECTION_NAME)

    # cleanup unused options
    for option in _CONFIG_PARSER.options(_MAIN_SECTION_NAME):
        if option not in _DEFAULTS.keys():
            _get_logger().debug("Removed obsolete config option : '%s'", option)
            _CONFIG_PARSER.remove_option(_MAIN_SECTION_NAME, option)

    # dump user config
    _get_logger().debug("***************************************************************************")
    _get_logger().debug("User config file dump - START")
    for option in _CONFIG_PARSER.options(_MAIN_SECTION_NAME):
        _get_logger().debug("%-30s : %s", option, _get(option))
    _get_logger().debug("User config file dump - END")
    _get_logger().debug("***************************************************************************")


def _setup_logging():
    """
    Sets up logging system.
    """

    global_log_format_string = '%(asctime)-15s %(threadName)-12s %(name)-20s %(levelname)-8s %(message)s'
    log_level = _LOG_LEVELS[_get(_LOG_LEVEL)]

    logging.basicConfig(level=log_level,
                        format=global_log_format_string,
                        filename=str(Path.home() / "als.log"),
                        filemode='w')

    # setup console log handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(global_log_format_string))
    logging.getLogger('').addHandler(console_handler)

    # in here, we maintain a list of third party loggers for which we don't want to see anything but WARNING & up
    third_party_polluters = [
        'watchdog.observers.inotify_buffer',
    ]
    for third_party_log_polluter in third_party_polluters:
        logging.getLogger(third_party_log_polluter).setLevel(logging.WARNING)


def _get_logger():
    return logging.getLogger(__name__)
