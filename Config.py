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

from configparser import ConfigParser
import os

# Local stuff
from resources import default_init_file_path
from resources import repo_init_file_path


class Config(ConfigParser):
    """
    This class is a helper that allows to automatically update config file on
    disk everytime something is changed in memory
    """
    def __init__(self, path=None):
        super().__init__()

        # In case path is None, try read from users home.
        # If it fails, read from local sources, and later on, save in user home
        if path is None:
            try:
                # als.ini is in user's home
                self.read(default_init_file_path)
                self._path = default_init_file_path
            except Exception as e:
                # init from local file
                super().read(repo_init_file_path)
                # write to als.ini in user's home
                self._path = default_init_file_path
                self.write()
        self._path = path

    def read(self):
        super().read(self._path)

    def write(self):
        with open(self._path, 'w') as f:
            super().write(f)
        print('Configuration written to {}'.format(self._path))

    def set(self, section, option, value):
        super().set(section, option, value)
        self.write()