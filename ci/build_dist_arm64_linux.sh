# this script builds a full dsitribution on a RPI4
#
# BEWARE : this is still experimental
#
# USAGE : MUST be called from the top of als sources dir
#
#######################################################################
set -ex

echo '###########################################################'
echo '## DEBUG python version:'
python --version
echo '###########################################################'

artifact_name="als-${ALS_VERSION_STRING}"

python -m venv venv
. venv/bin/activate
pip install -r ci/build_dist_arm64_linux_req.txt
python setup.py develop

echo "version = \"${ALS_VERSION_STRING}\"" > src/als/version.py

echo "Build of package ${artifact_name}..."

pyinstaller -n als-${ALS_VERSION_STRING} --windowed --hidden-import='pkg_resources.py2_warn' src/als/main.py

cd dist

tar zcf ../${artifact_name}.tgz ${artifact_name}
echo "Build of package ${artifact_name} completed OK."