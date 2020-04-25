# this script builds a full dsitribution
#
# BEWARE : this is still experimental and has only been
#          tested on a python3.6 system
#
# USAGE : MUST be called from the top of als sources dir
#
#######################################################################
set -e

python3 -m venv venv
. venv/bin/activate

pip install --upgrade pip
pip install wheel
pip install -r requirements.txt
pip install pyinstaller

python setup.py develop

VERSION=$(git describe --tags)

pyinstaller -n als-${VERSION} \
--add-data src/resources/index.html:resources \
--add-data src/resources/waiting.jpg:resources  \
--add-data src/als/main.css:. \
src/als/main.py

cd dist

tar zcvf als-${VERSION}.tgz als-${VERSION}