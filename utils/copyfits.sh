#!/usr/bin/env bash

set -e

if [[ -z $1 ]]
then
    echo "Missing argument : target scan folder"
    echo "Aborting..."
    exit 1
else
    SCAN=$1
fi

SAMPLES=image_samples

if [[ ! -d ${SCAN} ]]
then
    echo "Scan folder \"${SCAN}\" does not exist"
    echo "Aborting..."
    exit 2
fi

rm -rf ${SCAN}/*

for i in ${SAMPLES}/*.{fits,FITS,fit,FIT,jpg,JPG,jpeg,JPEG,cr2,CR2,arw,ARW,nef,NEF}
do
    if [[ -f "${i}" ]]  #to avoid fake outputs when extension isn't found
    then
        cp -v "${i}" ${SCAN}
        sleep 5
    fi
done

