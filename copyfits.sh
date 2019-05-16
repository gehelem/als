rm -rf ~/als/scan/*.fits

for i in `ls -d -1  ~/als/sample/Light_*.fits`
  do
 
  echo "$i"
  cp "$i" ~/als/scan
  sleep 1
 
done

