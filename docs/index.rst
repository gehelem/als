**ALS Astro Live Stacker**
===============================

ALS is a desktop application for fast and easy live stacking of astronomical images. It is a friend for
electronically assisted astronomers and astrophotographers.

.. figure:: ./_img/als-screenshot.png
   :alt: ALS main window
   :width: 100%

**ALS is not intrusive** : Keep your setup as it is and tell ALS to monitor the folder where your frames are saved.

Each time a new frame is captured and written to file, ALS aligns and stacks it with the previous ones.

**Pre-processing** applied to each frame before stacking:

- dark current subtraction (with your own master dark frame)
- hot pixel removal
- debayering of color images

**Post-processing** applied to each new stacking result :

- auto stretch
- levels adjustments
- RGB balance

Each processed image is **saved to disk** while ALS is waiting for the next frame.

Displayed image ca be **shared** on your network by a **built-in web server**, so your mates at the
astro club can see your wonderful images.

ALS can read FITS files as well as RAW files from all major camera manufacturers. The list of compatible RAW camera
formats is available at : https://www.libraw.org/supported-cameras

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Getting started

   Get ALS <get_als>
   First Run <first_run>

.. toctree::
   :maxdepth: 3
   :hidden:
   :caption: Geek corner

   Code documentation <api/modules>