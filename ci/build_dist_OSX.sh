# this script builds a full dsitribution
#
#          tested on a python3.6 system
#
# USAGE : MUST be called from the top of als sources dir
#
#######################################################################
set -e

pyenv local 3.6.9

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

pyinstaller -i src/resources/als_logo.icns -n als --windowed --exclude-module tkinter  src/als/main.py
cp -vf /usr/local/Cellar/libpng/1.6.37/lib/libpng16.16.dylib dist/als.app/Contents/MacOS

create-dmg --volname "ALS ${VERSION}" --window-pos 200 120 --window-size 800 400 --icon-size 100 --icon "als.app" 200 190 --hide-extension "als.app" --app-drop-link 600 185 "dist/ALS-${VERSION}.dmg" dist/als.app
