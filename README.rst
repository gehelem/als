========================
ALS - Astro Live Stacker
========================

.. image:: https://img.shields.io/travis/com/gehelem/als
.. image:: https://img.shields.io/github/license/gehelem/als

Description
===========

A standalone Python GUI application for live astrophotography stacking.

.. image:: docs/_static/als-screenshot.png
   :align: center

Features
========

ALS polls a folder on your machine and aligns + stacks any new picture saved into that folder.


ALS is compatible with `.fit` and `.fits` in 8bits and 16bits unsigned (B&W, RGB, and No Debayering)
and with RAW camera files : https://www.libraw.org/supported-cameras

As pictures are added to the stack, user can enhance the resulting image with various processes :

- contrast
- brightness
- levels
- RGB balance
- SCNR
- Wavelets

The resulting image can be saved to disk and served by a built-in web server, so your mates at the astro
club can see your wonderful images.

Installation
============

Until ALS is properly released to the usual software outlets, the best way to run ALS on your machine
is to use Python's virtual envs.

**The following install procedure has been tested on a freshly installed Ubuntu 18 LTS (a.k.a. Bionic). Your mileage
may vary.**

*All below commands have to be used in your terminal of choice.*

1. **Install a few system packages** :

- `git` to retrieve ALS sources
- `gcc` and `python3-dev` to compile some dependencies (don't be scared)
- `python3-venv` to handle virtualenvs

.. code-block::

  $ sudo apt update && sudo apt install -y git gcc python3-dev python3-venv


2. **Fetch ALS sources with the `refactor/structure` branch checked out**.
   This will create a folder named `als` wherever you currently are.

.. code-block::

  $ git clone https://github.com/gehelem/als -b refactor/structure


3. **Create your virtualenv with provided script**

   This will create a folder named `venv` inside the `als` folder, download and install all dependencies.

.. code-block::

  $ ./als/utils/venv_setup.sh

4. **Dive into the `als` folder**

.. code-block::

  $ cd als

5. **Activate the newly created virtualenv**

.. code-block::

  $ source venv/bin/activate

6. **Setup ALS into your virtualenv in development mode**. This is for now the only supported setup mode.
   This allows you to run ALS easily, as it adds a launcher script inside your active virtual env.

.. code-block::

  $ python setup.py develop

Launching ALS
=============

1. **Make sure your virtualenv is active**

   If your virtualenv is active, your command prompt is prepended with (venv). See example below :

.. code-block::

  (venv) user@host:~/als$

If you don't see the `(venv)` part before your command prompt, this means your virtualenv is not active.
Activate it using steps 4 & 5 of the `Installation`_ procedure.

2. **just launch ALS from anywhere** :)

.. code-block::

  $ als

Using ALS
=========

1. Launch ALS
2. Click the 'START' button

   If the configured scan folder does not exist, follow ALS advice and review your preferences

3. Setup you image acquisition system to save new pictures into the folder scanned by ALS
4. Start picture acquisition
5. Watch the magic do its work

Developing ALS
==============

On top of the steps described in `Installation`_ and `Launching ALS`_, you don't need much to start developing on ALS.

All you have to remember when you work on GUI: ALS uses the Qt framework. If you modify/create .ui files, you'll have to
recompile the corresponding Python modules. This is done by calling the following script : `utils/compile_ui_and_rc.sh`.
All .ui files MUST be located inside the `als.ui` package. Compiled modules are located in the
`als.generated` package.


For any other non GUI code, just edit the code and relaunch `als` each time you want to check your changes.

If you want to perform basic checks on the code before committing and pushing your changes, execute the
following command from within the `als` folder. If the script's exit code is 0 (zero), your code is safe
to be pushed. It may not yet do exactly what it is meant for, but at least it won't cause runtime errors
due to syntax errors.

.. code-block::

  $ ./ci/full_build.sh

Happy hacking !!!
