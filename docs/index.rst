ALS documentation
=================

ALS is a desktop application trying to perform fast and easy live stacking of astronomical images. It is a friend for
electronically assisted astronomers and astrophotographers.

.. figure:: ./_static/als-screenshot.png
   :alt: ALS main window
   :width: 100%

ALS is not intrusive : It simply polls the folder where your image acquisition system writes captured frames.
Each time a new frame is captured and written to file, ALS aligns and stacks it with the previous ones.

Pre-processing applied to each frame before stacking:

- dark current subtraction (with your own master dark frame)
- hot pixel removal
- debayering of color images

Post-processing applied to each new stacking result :

- auto stretch
- levels
- RGB balance

Each processing result is auto-saved to disk and can be served by a built-in web server, so your mates at the
astro club can see your wonderful images.

ALS can read FITS files as well as RAW files from all major camera manufacturers. The list of compatible RAW camera
formats is available at : https://www.libraw.org/supported-cameras

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Getting started

   Installation <installation>
   First Run <first_run>
