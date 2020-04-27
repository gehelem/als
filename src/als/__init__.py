# -*- coding: utf-8 -*-
"""The main ALS package"""
from pkg_resources import get_distribution, DistributionNotFound

try:
    DIST_NAME = __name__
    __version__ = get_distribution(DIST_NAME).version
except DistributionNotFound:
    __version__ = "0.7-dev"
finally:
    del get_distribution, DistributionNotFound
