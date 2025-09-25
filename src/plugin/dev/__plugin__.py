"""Plug-in metadata consumed by Rhino's Python plug-in loader."""

from __future__ import print_function

import os
import sys


_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from RhinoToSlicer import PLUGIN_ID, __version__

# Rhino expects the plug-in folder to include this identifier in its name.
id = "{{{}}}".format(PLUGIN_ID)

# The installer mirrors this version string to keep deployments in sync.
version = __version__

# Human friendly name that Rhino displays in the plug-in manager.
title = "RhinoToSlicer"


def OnLoadPlugIn():
    """Optional hook that runs when Rhino loads the plug-in."""

    try:
        import Rhino
    except ImportError:
        return

    Rhino.RhinoApp.WriteLine("RhinoToSlicer {0} ready (command: SendToPrusa).".format(__version__))
