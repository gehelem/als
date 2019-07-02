import os
from pathlib import Path

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

default_init_file_path = os.path.join(str(Path.home()), 'als.ini')
repo_init_file_path = os.path.join(__location__, 'als.ini')
dslr_icon_path = os.path.join(__location__, 'dslr-camera.svg')
