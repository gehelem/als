# this script builds a full dsitribution on a RPI4
#
# BEWARE : this is still experimental
#
# USAGE : MUST be called from the top of als sources dir
#
#######################################################################
set -e

if [ ! -d venv ]
then
  python3 -m venv --system-site-packages venv
fi

. venv/bin/activate

pip install --upgrade pip
pip install --upgrade wheel

patch < ci/rpi4_requirements.patch
pip install -I -r requirements.txt

python setup.py develop

VERSION=$(grep __version__ src/als/__init__.py | tail -n1 | cut -d'"' -f2)

if [ -z "${VERSION##*"dev"*}" ] ;then
  VERSION=${VERSION}-$(git rev-parse --short HEAD)
fi

pyinstaller -n als-${VERSION} --windowed --hidden-import='pkg_resources.py2_warn' src/als/main.py

cd dist

tar zcf als-${VERSION}.tgz als-${VERSION}