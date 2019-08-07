# Astro Live Stacker
Astro Live Stacker is an application that allows stacking of astronomy images
in real time, as they come from a camera sensors. 

It monitors a certain directory for new FITS images, aligns the stars in them,
and does a Sum or Mean stacking.

The application is writting in Python3, QT5, and other dependecies detailed below.

## Requirements
The following Python3 libraries are required.

If you follow the installation procedures detailed below, then you do not need to
worry about these dependencies, since the installation procedure will take care of
them. 

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

## Installation
The easiest, and more fool proof way to install ALS, is via Python Virtual Environment (venv).

### Linux (All variants):
You first need to install ALS itself.

Download the .zip archive of the alpha branch, and extract it
Rename the `als-alpha` folder to `als`

Alternately, if you are a developer, you can use git to clone the alpha branch of the repository
to your home directory using the following commands:
```
git clone https://github.com/gehelem/als.git
cd ~/als 
git checkout alpha
```
Whichever way you installed ALS, you need to perform the following additional steps:
```
cd ~/als 
mkdir scan  
mkdir wrk
```
## Installing Dependencies via Python venv
```
sudo apt install python3
./venv_setup.sh
```

## Linux Manual Installation
### Desktop/Laptop (amd64):
```
sudo apt update
sudo apt install python3 python3-pip git
pip3 install astropy numpy tqdm watchdog pyqt5 astroalign opencv-python rawpy python-gettext pywi dtcwt
```  
### ARM (arm64/armv8/aarch64):
```
sudo apt install python3 python3-dev gfortran libopenblas-dev liblapack-dev
pip3 install wheel
pip3 install astropy numpy tqdm watchdog astroalign rawpy python-gettext pywi dtcwt
sudo apt install python3-opencv python3-pyqt5
```  

## Windows Installation
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

## Running ALS

### On Ubuntu or Debian:
You can run ALS by calling this script from the command line. This script should work the same way,
regardless of the installation method.

You can also add this script to your KDE, Gnome or XFCE launcher.
```
~/als/als.sh
```

### On Windows:
Run __CMD__ :  
Go in ALS folder with __cd__ command  
and run ALS with :  
`python ~/als/als.py` or `python3 ~/als/als.py`
      
### Warning 

For windows, need change default __wrk__ and __save__ folder path in GUI __before__ Play.

## Testing Your Installation
Before running ALS with your own files, you need to verify that everything is 
installed correctly. To do this, start ALS, click on Play, then run the following script:

```
cd ~/als
./testfits.sh
```

### Input :

ALS is compible with `.fit` and `.fits` in 8bits and 16bits unsigned (B&W, RGB, and No Debayering)  
and with RAW camera file : https://www.libraw.org/supported-cameras

### Output :

ALS produce 0 or 1 output in work folder: 
- (option) stack_xxxxxx.fit/fits --> It's the recording of the intermediate raw images of the stack

### Developments
In order to compile ui and qrc resource file to be used in the project, please use the following commands:
```bash
  pyuic5 ./alsui.ui -o ./alsui.py 
  pyrcc5 ./resources_dir/resource.qrc -o ./resource_rc.py
```

