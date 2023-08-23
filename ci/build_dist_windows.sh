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
  VERSION=$(grep version src/als/version.py | cut -d'"' -f2)-$(git rev-parse --short HEAD)
fi

VERSION=$(echo ${VERSION} | sed "s/^v//")
echo "version = \"${VERSION}\"" > src/als/version.py

VERPARTS=(${VERSION//-/ })
VERNUM=${VERPARTS[0]}
DOTCOUNT=$(grep -o '\.' <<< "${VERNUM}" | grep -c .)

for (( c=${DOTCOUNT}; c<3; c++ ))
do
  VERNUM=${VERNUM}.0
done

VERCODE=$(echo ${VERNUM} | sed "s/\./, /g")

echo "Building package version: ${VERSION}"

sed -e "s/##VERSION##/${VERSION}/g" -e "s/##VERCODE##/${VERCODE}/g" ci/file_version_info_template.txt > ci/file_version_info.txt

pyinstaller --hidden-import "pkg_resources.py2_warn" -i src/resources/als_logo.ico -F -n als --windowed --version-file=ci/file_version_info.txt --add-data 'src/resources/qt.conf:.' src/als/main.py
