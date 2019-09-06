# Astro Live Stacker

__Python 3 library required__
- pyqt5 (GUI)
- watchdog (new file checking)
- numpy 
- astropy (to save and read fit file)
- tqdm (for %)
- astroalign (frame alignement)
- cv2 ( TIFF saving and debayering)
- rawpy ( convert RAW camera file to RGB)
- dtcwt (for wavelets)
- pywi (for wavelets)

## Install process (On ubuntu or debian (min buster)): 

`sudo apt update` (adapte for other unix system)  
`sudo apt install python3 python3-pip git` (adapte for other unix system) 
### for amd64 (classique computer) :
`pip3 install astropy numpy tqdm watchdog pyqt5 astroalign opencv-python rawpy python-gettext pywi dtcwt`  
### for arm64/armv8/aarch64 :  
`sudo apt install python3 python3-dev gfortran libopenblas-dev liblapack-dev`  
`pip3 install wheel`  
`pip3 install astropy numpy tqdm watchdog astroalign rawpy python-gettext pywi dtcwt`   
`sudo apt install python3-opencv python3-pyqt5`  
### for arm32/armv7/armhf :  

____________________  
cd ~`  
`git clone https://github.com/gehelem/als.git`  (or just download als on github)  
`cd ./als`  
`mkdir scan`  
`mkdir wrk`  

## Install process (On Windows):
__(option) Warning :__ Need uninstall Python 2.x.x before install process


Go to -> https://www.python.org/downloads/  
Download python 3.7.x for your system.  
__Warning :__ select : pip (PiPy) and add to windows path  

After, Run __CMD__ in administrator mode (right click on __CMD__):  
`pip install astropy numpy tqdm watchdog pyqt5 astroalign opencv-python rawpy python-gettext dtcwt pywi`  
or  
`pip3 install astropy numpy tqdm watchdog pyqt5 astroalign opencv-python rawpy python-gettext dtcwt pywi`

Download als on github : https://codeload.github.com/gehelem/als/zip/master  
Extract ALS


## For Run (On ubuntu or unix system):
`python3 ~/als/als.py`

## For Run (On Windows):
Run __CMD__ :  
Go in ALS folder with __cd__ command  
and run ALS with :  
`python ~/als/als.py` or `python3 ~/als/als.py`
      
________________________________
### Warning 

For windows, need change default __wrk__ and __save__ folder path in GUI __before__ Play.

### Input :

ALS is compible with `.fit` and `.fits` in 8bits and 16bits unsigned (B&W, RGB, and No Debayering)  
and with RAW camera file : https://www.libraw.org/supported-cameras

### Output :

ALS produce 0 or 1 output in work folder: 
- (option) stack_xxxxxx.fit/fits --> It's the recording of the intermediate raw images of the stack

### Developments
In order to compile ui and qrc resource file to be used in the project, please use the following command:
```bash
    utils/compile_ui_and_rc.sh
```

