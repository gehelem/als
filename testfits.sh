# This is a test script for ALS
# To use it, press the Play button, then run this script
# It will copy images of M27 to the scan directory, and
# will be able to verify if ALS works as planned

DIR_ALS=~/als
DIR_SCAN=$DIR_ALS/scan

rm -rf $DIR_SCAN/*.fits

for FILE in `ls -d -1 $DIR_ALS/sample/Light_*.fits`
  do
 
  echo "$FILE"
  cp "$FILE" $DIR_SCAN

  sleep 3
 
done

