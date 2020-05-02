@echo off

python -m venv venv
CALL venv\Scripts\activate
		
pip install --upgrade pip
pip install --upgrade wheel
pip install --upgrade setuptools
pip install numpy==1.16.4
pip install -r requirements.txt

python setup.py develop

pyinstaller -F -n als --windowed --hidden-import=pkg_resources.py2_warn src/als/main.py

