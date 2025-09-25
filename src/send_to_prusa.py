"""Compatibility wrapper for legacy installs.

This module proxies to the packaged RhinoToSlicer plug-in so that existing
macros using ``import send_to_prusa`` continue to function.
"""

from RhinoToSlicer.commands.send_to_prusa import *  # noqa: F401,F403
