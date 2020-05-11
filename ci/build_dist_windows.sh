# this script builds a full ALS distribution
#
# BEWARE : this is still experimental and has only been
#          tested on a win10/Python3.7 system with git bash
#
# USAGE : MUST be called from the top of als sources dir
#
#######################################################################
set -e

python -m venv venv
. venv/Scripts/activate

python -m pip install --upgrade pip
pip install wheel
pip install setuptools
pip install $(grep numpy requirements.txt)
pip install -r requirements.txt
pip install --upgrade astroid==2.2.0

python setup.py develop

./ci/pylint.sh

VERSION=$(grep __version__ src/als/__init__.py | tail -n1 | cut -d'"' -f2)

if [ -z "${VERSION##*"dev"*}" -a -d .git ] ;then
  VERSION=${VERSION}-$(git rev-parse --short HEAD)
fi

pyinstaller -i src/resources/als_logo.ico -F -n als-${VERSION} --windowed src/als/main.py
