#rm -rf ./scan/*.fits

for i in `ls -d -1  ./sample/Light_*.fits`
  do
 
  echo "$i"
  cp "$i" ./scan
  sleep 1
 
done

