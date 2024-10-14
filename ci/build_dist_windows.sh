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

VERSION=$(echo ${ALS_VERSION_STRING} | sed "s/^v//")
artifact_name="als-${VERSION}"
echo "version = \"${VERSION}\"" > src/als/version.py

VERPARTS=(${VERSION//-/ })
VERNUM=${VERPARTS[0]}
DOTCOUNT=$(grep -o '\.' <<< "${VERNUM}" | grep -c .)

for (( c=${DOTCOUNT}; c<3; c++ ))
do
  VERNUM=${VERNUM}.0
done

VERCODE=$(echo ${VERNUM} | sed "s/\./, /g")

echo "Building package ${artifact_name}.exe ..."
sed -e "s/##VERSION##/${VERSION}/g" -e "s/##VERCODE##/${VERCODE}/g" ci/file_version_info_template.txt > ci/file_version_info.txt
pyinstaller -i src/resources/als_logo.ico -F -n ${artifact_name} --windowed --version-file=ci/file_version_info.txt --add-data 'src/resources/qt.conf:.' src/als/main.py
echo "Build of package ${artifact_name}.exe completed OK."
