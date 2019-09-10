#!/usr/bin/env bash
set -e

echo "******* compiling Qt resources : Start"

SRC=$(readlink -f $(dirname $(readlink -f ${0}))/../src)
GENERATED=${SRC}/generated

echo "UI files ..."

for ui in ${SRC}/als/ui/*.ui
do
    py=${GENERATED}/$(basename ${ui/.ui/.py})
    echo "Executing : pyuic5 ${ui} -o ${py} --import-from=${GENERATED/*src\//}"
    pyuic5 ${ui} -o ${py} --import-from=${GENERATED/*src\//}
done

echo "RC files ..."

for rc in ${SRC}/resources/*.qrc
do
    py=${GENERATED}/$(basename ${rc/.qrc/_rc.py})
    echo "Executing : pyrcc5 ${rc} -o ${py}"
    pyrcc5 ${rc} -o ${py}
done

echo "******* compiling Qt resources : Done"

