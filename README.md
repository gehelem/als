# Astro Live Stacker

__Python 3 library required__
- pyqt5 (GUI)
- watchdog (new file checking)
- numpy 
- astropy (to save and read fit file)
- tqdm (for %)
- astroalign (frame alignement)
- cv2 ( TIFF saving and debayering)

## Install process (On ubuntu or debian): 

`sudo apt update` (adapte for other unix system)  
`sudo apt install python3 python3-pip git` (adapte for other unix system)   
`pip3 install astropy numpy tqdm watchdog pyqt5 astroalign opencv-python`  
`cd ~`  
`git clone https://github.com/gehelem/als.git`  (or just download als on github)  
`cd ./als`  
`mkdir scan`  
`mkdir wrk`  

## Install process (On Windows):
__Warning :__ Need uninstall Python 2.x.x before install process


Go to -> https://www.python.org/downloads/  
Download python 3.7.x for your system.  
__Warning :__ select : pip (PiPy) and add to windows path  

After, Run __CMD__ in administrator mode :  
`pip install astropy numpy tqdm watchdog pyqt5 astroalign opencv-python`  
or  
`pip3 install astropy numpy tqdm watchdog pyqt5 astroalign opencv-python`

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

ALS produce 3 output in work folder: 
- first_stack_ref.fit --> Xbits file unsigned, no header, RGB --> It's first image for align reference
- stack_ref_image.fit --> Xbits file unsigned, no header, RGB --> It's actual stack raw image
- stack_image.tiff --> Xbits file, RGB, TIFF format --> It's preview of actual stack image with contrast/luminosity correction
- (option) stack_xxxxxx.fit/fits --> It's the recording of the intermediate raw images of the stack
