# this script builds a full distribution
#
#          tested on a python3.6 system
#
# USAGE : MUST be called from the top of als sources dir
#
#######################################################################
set -e

venv_name="venv"
artifact_name="als-${ALS_VERSION_STRING}.dmg"

pyenv local 3.6.9
python -m venv "${venv_name}"
. "${venv_name}"/bin/activate
pip install -r requirements.txt

python setup.py develop

echo "version = \"${ALS_VERSION_STRING}\"" > src/als/version.py

echo "Building package ${artifact_name} ..."

pyinstaller -i src/resources/als_logo.icns -n als --windowed --exclude-module tkinter  src/als/main.py
cp -vf /usr/local/Cellar/libpng/1.6.44/lib/libpng16.16.dylib dist/als.app/Contents/MacOS
sed -e "s/##VERSION##/${ALS_VERSION_STRING}/"  ci/Info.plist > dist/als.app/Contents/Info.plist
create-dmg --volname "ALS ${ALS_VERSION_STRING}" --window-pos 200 120 --window-size 500 300 --icon-size 100 --icon "als.app" 120 140 --hide-extension "als.app" --app-drop-link 370 140 --background src/resources/starfield.png ${artifact_name} dist/als.app
echo "Build of package ${artifact_name} completed OK."