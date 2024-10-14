# this script builds a full ALS distribution
#
# BEWARE : this is still experimental and has only been
#          tested on a python3.6 system
#
# USAGE : MUST be called from the top of als sources dir
#
#######################################################################
set -e

venv_name="alsbuild${CI_PIPELINE_ID}"
artifact_name="als-${ALS_VERSION_STRING}.run"

pyenv local 3.6.9
pyenv virtualenv "${venv_name}"
. ~/.pyenv/versions/${venv_name}/bin/activate
pip install -r requirements.txt
python setup.py develop

./ci/pylint.sh

echo "version = \"${ALS_VERSION_STRING}\"" > src/als/version.py


echo "Building package ${artifact_name} ..."
pyinstaller -F -n "${artifact_name}" --windowed src/als/main.py
echo "Build of package ${artifact_name} completed OK."

