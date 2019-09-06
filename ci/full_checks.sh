#!/usr/bin/env bash
#
# launch all needed checks agains whole ALS codebase
#
###########################################################################

# check pylint on als package and return nonzero only in these cases :
#
#  - pylint encountered a fatal error
#  - pylint found errors in the code
#  - pylint was incorrectly invoked


echo "**********************************************************************"
echo "******** pylint analysis launch"
echo "**********************************************************************"

pylint src/als
rc=$?

FATAL_ERROR=1
ERRORS_FOUND=2
USAGE_ERROR=32

if [[ $((${rc} & ${FATAL_ERROR})) -ne 0 || $((${rc} & ${ERRORS_FOUND}))  -ne 0 || $((${rc} & ${USAGE_ERROR})) -ne 0 ]]
then
    echo "******** Failing the build because of pylint errors"
    exit 1
else
    echo "******** Build passes : no errors found by pylint"
    exit 0
fi