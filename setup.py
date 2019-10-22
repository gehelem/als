# -*- coding: utf-8 -*-
"""
Installs ALS.

We added a custom command to override develop and install
in order to have Qt resources (UI and images) compiled and
put in place
"""
import os
import sys

from pkg_resources import VersionConflict, require
from setuptools import setup

from utils import compile_ui_and_rc

try:
    require('setuptools>=38.3')
except VersionConflict:
    print("Error: version of setuptools is too old (<38.3)!")
    sys.exit(1)

if __name__ == "__main__":

    if any([command in ['develop', 'install'] for command in sys.argv[1::]]):
        compile_ui_and_rc.main()

    setup(use_pyscaffold=True)
