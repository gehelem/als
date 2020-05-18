# this script builds a full distribution
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

tags=$(git tag --contains HEAD)

if [ -z "${tags}" ]
then
  tag_count=0
else
  tag_count=$(echo "${tags}" | wc -l)
fi

if [ ${tag_count} -gt 1 ]
then
    echo "More that one tag exist on HEAD. Cancelling ..."
    exit 1
fi

if [ $tag_count -eq 1 ]
then
  VERSION=$(git tag --contains HEAD)
else
  VERSION=$(grep version version.py | cut -d'"' -f2)-$(git rev-parse --short HEAD)
fi

echo "version = \"${VERSION}\"" > version.py

echo "Building package version: ${VERSION}"

pyinstaller -i src/resources/als_logo.icns -n als --windowed --exclude-module tkinter  src/als/main.py
cp -vf /usr/local/Cellar/libpng/1.6.37/lib/libpng16.16.dylib dist/als.app/Contents/MacOS
sed -e "s/##VERSION##/${VERSION}/"  ci/Info.plist > dist/als.app/Contents/Info.plist

create-dmg --volname "ALS ${VERSION}" --window-pos 200 120 --window-size 500 300 --icon-size 100 --icon "als.app" 120 140 --hide-extension "als.app" --app-drop-link 370 140 --background src/resources/starfield.png dist/ALS-0.7-${VERSION}.dmg dist/als.app
