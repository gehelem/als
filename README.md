# Astro Live Stacker

__Python 3 library required__
- pyqt5 (GUI)
- watchdog (new file checking)
- numpy 
- astropy (to save and read fit file)
- tqdm (for %)
- astroalign (frame alignement)
- cv2 ( TIFF saving and debayering)

##Install process (On ubuntu or debian): 

sudo apt update  
sudo apt install python3-opencv python3-pip git   
pip3 install astropy numpy tqdm watchdog pyqt5 astroalign  
cd ~  
git clone https://github.com/gehelem/als.git  
cd ./als  
mkdir scan  
mkdir wrk  

##For Run :
python3 ~/als/als.py
