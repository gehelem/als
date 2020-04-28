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

VERSION=$(grep __version__ src/als/__init__.py | tail -n1 | cut -d'"' -f2)

if [ -z "${VERSION##*"dev"*}" ] ;then
  VERSION=${VERSION}-$(git rev-parse --short HEAD)
fi

pyinstaller -F -n als-${VERSION} --windowed src/als/main.py

