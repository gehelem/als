ALS documentation
=================

.. figure:: ./_static/als-screenshot.png
   :alt: ALS
   :width: 100%

ALS is a desktop application trying to perform fast and easy live stacking of astronomical images. It is a friend for
electronically assisted astronomers and astrophotographers.

It works by polling the folder where your image acquisition system writes captured frames.
Each time a new frame is captured and written to file, ALS aligns and stacks it with the previous ones.

Before alignment, these pre-processors are applied to each frame :

- dark current subtraction (with your own master dark frame)
- hot pixel removal
- debayering of color images

After alignment, these post-processors are applied to the new stacking result :

- auto stretch
- levels
- RGB balance

Configuration for the pre-processors is done in the preferences panel. Post-processors can be tweaked live with
controls on ALS's main window.

The latest processing result is auto-saved to disk and can be served by a built-in web server, so your mates at the
astro club can see your wonderful images.

ALS can read FITS files and RAW files from all major camera manufacturers. The list of compatible RAW camera formats is
at : https://www.libraw.org/supported-cameras



.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Getting started

   Installation <installation>
   First Run <first_run>
