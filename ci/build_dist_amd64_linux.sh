# this script builds a full ALS distribution
#
# BEWARE : this is still experimental and has only been
#          tested on a python3.6 system
#
# USAGE : MUST be called from the top of als sources dir
#
#######################################################################
set -e

artifact_name="als-${ALS_VERSION_STRING}.run"

pyenv local 3.6.9
python -m venv venv
. ./venv/bin/activate
pip install -r requirements.txt
python setup.py develop

echo "version = \"${ALS_VERSION_STRING}\"" > src/als/version.py

echo "Building package ${artifact_name} ..."
pyinstaller -F -n "${artifact_name}" --windowed src/als/main.py
mv dist/${artifact_name} .
echo "Build of package ${artifact_name} completed OK."

