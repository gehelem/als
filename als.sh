#!/bin/sh

cd $HOME/als

if [ -d venv ]; then
  . venv/bin/activate
  PYTHON=python
else
  PYTHON=python3
fi

$PYTHON ./als.py
