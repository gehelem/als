set -e

###########################################################################
#
# compute version number for current tag and/or hash
#
###########################################################################

tags=$(git tag --contains HEAD)

if [ -z "${tags}" ]
then
  tag_count=0
else
  tag_count=$(echo "${tags}" | wc -l)
fi

if [ ${tag_count} -gt 1 ]
then
    echo "More that one tag exist on HEAD. Cancelling ..."
    exit 1
fi

if [ $tag_count -eq 1 ]
then
  VERSION=$(git tag --contains HEAD)
else
  VERSION=$(grep version src/als/version.py | cut -d'"' -f2)-$(git rev-parse --short HEAD)
fi



###########################################################################
#
# export all variables in .dotenv file
#
###########################################################################
echo "ALS_VERSION_STRING=${VERSION}" > .dotenv



###########################################################################
#
# dump created env file
#
###########################################################################
echo '######### env file dump START'
cat .dotenv
echo '######### env file dump END'

