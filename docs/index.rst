ALS documentation
=================

ALS is a desktop application  trying to perform fast and easy live stacking of astronomical images, wether it be for
electronically assisted astronomy or monitoring a running astrophotography session.

It works by polling the folder where your usual image acquisition system writes captured images.
Each time a new image is captured and written to file, ALS aligns and stacks that image with the
previous ones.

Before alignment, these pre-processors are applied to each frame :

- dark current subtraction (with your own master dark frame)
- hot pixel removal
- debayering of color images

After alignment, these post-processors are applied to the new stacking result :

- auto stretch
- levels
- RGB balance

Configuration for the pre-processors is done in the preferences panel.
Post-processors can be tweaked live with controls on ALS's main window.

.. figure:: ./_static/als-screenshot.png
   :alt: Siril
   :class: with-shadow
   :width: 800px

The latest processing result is auto-saved to disk and can be served by a built-in web server,
so your mates at the astro club can see your wonderful images.

ALS can read FITS files and RAW files from all major camera manufacturers. The list of compatible RAW camera formats is
at : https://www.libraw.org/supported-cameras



.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Getting started

   Installation <installation>
   First Run <first_run>

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Geek corner

   Code documentation <api/modules>