#!/usr/bin/env bash
set -e
echo "******* compiling Qt resources : Start"

GENERATED=src/generated

for ui in src/als/*.ui
do
    py=${GENERATED}/$(basename ${ui})
    py=${py/.ui/.py}
    echo "Executing : pyuic5 ${ui} -o ${py} --import-from=generated"
    pyuic5 ${ui} -o ${py} --import-from=generated
done

for ui in src/resources/*.qrc
do
    py=${GENERATED}/$(basename ${ui})
    py=${py/.qrc/_rc.py}
    echo "Executing : pyrcc5 ${ui} -o ${py}"
    pyrcc5 ${ui} -o ${py}
done

echo "******* compiling Qt resources : Done"

