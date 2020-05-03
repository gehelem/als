# this script builds a full ALS distribution
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

pyinstaller -F -n als-${VERSION} --windowed src/als/main.py

