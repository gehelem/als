#!/usr/bin/env bash
set -e
echo "*********** compiling Qt resources : Start"
for ui in src/als/*.ui
do
    py=src/als/generated/$(basename ${ui})
    py=${py/.ui/.py}
    echo "Executing : pyuic5 ${ui} -o ${py} --import-from=als.generated"
    pyuic5 ${ui} -o ${py} --import-from=als.generated
done

pyrcc5 src/als/resources/resource.qrc -o src/als/generated/resource_rc.py
echo "*********** compiling Qt resources : Done"

