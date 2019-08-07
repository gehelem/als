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

# Check if we have a requirements file
if ! [[ -r requirements.txt ]]
then
    echo "Error : Please make sure you run this script from within the als directory"
    exit 1
fi

# Update package list
sudo apt-get update

# Install venv
sudo apt-get install python3-venv

# Create the venve
python3 -m venv venv

# Load the needed environment variables
source venv/bin/activate

# Now install all the needed Python stuff
pip install -r requirements.txt

# Automatically create the directories
for DIR in wrk scan
do
	if [ ! -d $DIR ]; then
		mkdir $DIR
	fi
done
