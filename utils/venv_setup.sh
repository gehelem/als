#!/usr/bin/env bash
#
# venv_setup.sh
###############
#
# This will install a custom python3 virtual environment in the specified folder.
# If no folder is specified, the virtualenv is created in a folder named 'venv', located inside the als folder.
#
# This script will work on any reasonably recent Debian-based GNU/Linux Distribution. Yes, Ubuntu is one of them
#
# Simply run this script & give your password to the sudo commands (required to install 1 new package into
# your system)
# The result is a directory that contains a full python3 working environment with all external libraries
# needed by als.
#
# WARNING : the resulting directory is quite heavy : around 800MB
#
# enjoy :)
#
# This script takes 1 optional parameter :
#
# - The path of the new virtualenv folder (defaults to <als_sources_dir>/venv)
#################################################################################

set -e

PRJ=$(readlink -f $(dirname $(readlink -f ${0}))/../)

cd ${PRJ}

sudo apt-get update
sudo apt-get install -y python3-venv
VENV=${1:-${PRJ}/venv}
echo "Creating virtual env in : ${VENV} ..."
python3 -m venv ${VENV}
source ${VENV}/bin/activate
pip install --upgrade pip
pip install wheel
pip install setuptools
pip install $(grep numpy ${PRJ}/requirements.txt)
pip install -r ${PRJ}/requirements.txt
pip install --upgrade astroid==2.2.0

echo "Virtualenv setup is complete"

