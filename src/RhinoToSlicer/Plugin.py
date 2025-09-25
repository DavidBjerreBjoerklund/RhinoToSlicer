"""Rhino plug-in entry point for RhinoToSlicer.

The :mod:`plugindef` module exposes metadata for Rhino's Python plug-in loader
while this module defines the plug-in class responsible for loading commands
when Rhino activates the plug-in.
"""

import Rhino
import System

from . import __version__
from .plugindef import _COMMAND_ID, _PLUGIN_ID  # reuse identifiers defined there

__all__ = ["plug_in", "RhinoToSlicerPlugIn"]


class RhinoToSlicerPlugIn(Rhino.PlugIns.PlugIn):
    """Minimal plug-in that ensures commands are registered on load."""

    def __init__(self):
        Rhino.PlugIns.PlugIn.__init__(self)

    def PlugInID(self):  # noqa: N802 - Rhino API camelCase requirement
        return System.Guid(_PLUGIN_ID)

    def OnLoad(self, error_number):  # noqa: N802 - Rhino API camelCase requirement
        # Import the command module so the SendToPrusa command registers itself.
        from .commands import send_to_prusa  # noqa: F401

        Rhino.RhinoApp.WriteLine(
            "RhinoToSlicer {0} initialized (command id: {1}).".format(__version__, _COMMAND_ID)
        )
        return Rhino.PlugIns.LoadReturnCode.Success


# Expose a module-level reference so Rhino can instantiate the plug-in.
plug_in = RhinoToSlicerPlugIn()
