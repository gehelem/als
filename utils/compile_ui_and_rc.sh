#!/usr/bin/env bash
set -e

echo "******* compiling Qt resources : Start"

SRC=$(readlink -f $(dirname $(readlink -f ${0}))/../src)
GENERATED=${SRC}/generated

echo "UI files ..."

for ui in ${SRC}/als/ui/*.ui
do
    py=${GENERATED}/$(basename ${ui/.ui/.py})
    COMMAND="pyuic5 ${ui} -o ${py} --import-from=${GENERATED/*src\//}"
    echo "Executing : ${COMMAND}"
    eval ${COMMAND}
done

echo "RC files ..."

for rc in ${SRC}/resources/*.qrc
do
    py=${GENERATED}/$(basename ${rc/.qrc/_rc.py})
    COMMAND="pyrcc5 ${rc} -o ${py}"
    echo "Executing : ${COMMAND}"
    eval ${COMMAND}
done

echo "******* compiling Qt resources : Done"

