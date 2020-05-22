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

echo "version = \"${VERSION}\"" > src/als/version.py

echo "Building package version: ${VERSION}"

pyinstaller -i src/resources/als_logo.ico -F -n als-${VERSION} --windowed src/als/main.py
