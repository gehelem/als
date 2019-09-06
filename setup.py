# -*- coding: utf-8 -*-
"""
    Setup file for als.
    Use setup.cfg to configure your project.

    This file was generated with PyScaffold 3.2.1.
    PyScaffold helps you to put up the scaffold of your new Python project.
    Learn more under: https://pyscaffold.org/
"""
import os
import sys

from pkg_resources import VersionConflict, require
from setuptools import setup
from setuptools.command.install import install

try:
    require('setuptools>=38.3')
except VersionConflict:
    print("Error: version of setuptools is too old (<38.3)!")
    sys.exit(1)


class AlsInstall(install):
    def run(self):
        print("************* ALS Pre-Build steps : START")
        AlsInstall.compile_qt_resources()
        print("************* ALS Pre-Build steps : END")
        install.run(self)

    @staticmethod
    def compile_qt_resources():
        os.system('utils/compile_ui_and_rc.sh')


if __name__ == "__main__":
    setup(use_pyscaffold=True, cmdclass={'install': AlsInstall, 'develop': AlsInstall})
