set -e

TIMESTAMP=$(echo -n "${CI_PIPELINE_CREATED_AT}" | cut -d'T' -f1)

if [ -z "${CI_NIGHTLIES_ROOT}" ]
then
  echo "No root folder defined for nightlies. EXITING"
  exit 1  
fi

export NEW_FOLDER_NAME=${TIMESTAMP}-${CI_COMMIT_SHORT_SHA}
TARGET_FOLDER=${CI_NIGHTLIES_ROOT}/${NEW_FOLDER_NAME}

mkdir "${TARGET_FOLDER}"

cp als*.{exe,dmg,run,tgz} "${TARGET_FOLDER}"/

export ALS_AMD64_LINUX_ARTIFACT_NAME=$(ls als*.run)
export ALS_AMD64_WIN_ARTIFACT_NAME=$(ls als*.exe)
export ALS_AMD64_OSX_ARTIFACT_NAME=$(ls als*.dmg)
export ALS_ARM64_LINUX_ARTIFACT_NAME=$(ls als*.tgz)

envsubst < ci/deploy/nightlies_index_template.html > ${TARGET_FOLDER}/index.html

rm -rf ${CI_NIGHTLIES_ROOT}/latest
cp -r ${TARGET_FOLDER} ${CI_NIGHTLIES_ROOT}/latest

