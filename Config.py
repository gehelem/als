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


class Config(ConfigParser):
    """
    This class is a helper that allows to automatically update config file on
    disk everytime something is changed in memory
    """
    def __init__(self, path='config.ini'):
        super().__init__()
        self._path = path

    def read(self):
        super().read(self._path)

    def set(self, section, option, value):
        super().set(section, option, value)
        with open(self._path, 'w') as f:
            super().write(f)
        print('Configuration written to {}'.format(self._path))