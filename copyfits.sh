rm -rf ~/als/scan/*.fits

#for i in `ls -d -1  /home/gilles/ekos/siril/m51/Light/lum/Light_*.fits`
for i in `ls -d -1  /home/gilles/als/sample/Light_*.fits`
  do
 
  echo "$i"
  cp "$i" ~/als/scan
  sleep 3
 
done

