#!/usr/bin/env bash
set -e
pyuic5 src/als/als_ui.ui -o src/als/generated/als_ui.py --import-from=als.generated
pyuic5 src/als/about_ui.ui -o src/als/generated/about_ui.py --import-from=als.generated
pyuic5 src/als/prefs_ui.ui -o src/als/generated/prefs_ui.py --import-from=als.generated
