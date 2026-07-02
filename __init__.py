# -*- coding: utf-8 -*-
"""
Online Map Clipper plugin initialization.
"""
from .online_map_clipper import OnlineMapClipper

def classFactory(iface):
    return OnlineMapClipper(iface)