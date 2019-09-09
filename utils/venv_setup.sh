#!/usr/bin/env bash

# This will install a python3 virtual environment in the als directory.
#
# This script will work on any reasonably recent Debian - based GNU/Linux Distribution. Yes, Ubuntu is one of them
#
# Simply run this script & give your password to the sudo commands (required to install 1 new package into your system)
#
# The result is a 'venv' directory that contains a full python3 working environment with all external libraries
# needed by als.
#
# WARNING : the resulting 'venv' directory is quite heavy : around 720MB
#
# enjoy :)

set -e

PRJ=$(readlink -f $(dirname $(readlink -f ${0}))/../)

cd ${PRJ}

sudo apt-get update
sudo apt-get install python3-venv
python3 -m venv ${PRJ}/venv
source ${PRJ}/venv/bin/activate
pip install --upgrade pip
pip install -r ${PRJ}/requirements.txt

echo "Virtualenv setup is complete"

