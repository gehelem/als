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

ALS polls a folder on your machine and aligns + stacks any new image written in that folder.
User can then enhance the resulting image with various processes :

- contrast
- brightness
- levels
- RGB balance
- SCNR
- Wavelets

Resulting image can also be served by a built-in web server, so your mates at the astro club can see
your wonderful images.

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


2. **Fetch ALS sources with the `develop` branch checked out**.
   This will create a folder named `als` wherever you currently are.

.. code-block::

  $ git clone https://github.com/gehelem/als -b develop


3. **Create your virtualenv with provided script**

   This will create a folder named `venv` inside the `als` folder.

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

TODO

Developing ALS
==============

You don't need anything else than the steps described in `Installation`_ and `Launching ALS`_ to have a working
development environment.

Just edit the code and launch `als` each time you want to check your changes.

If you want to perform basic checks on the code before committing and pushing your changes, execute the
following command from within the `als` folder. If the script's exit code is 0 (zero), your code is safe
to be pushed. It may not yet do exactly what it is meant for, but at least it won't cause runtime errors
due to syntax errors.

.. code-block::

  $ ./ci/full_build.sh

Happy hacking !!!
