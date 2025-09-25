"""Rhino command shim that delegates to the RhinoToSlicer helper module."""

from __future__ import print_function

import os
import sys

from Rhino.Commands import Result

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from RhinoToSlicer.commands import slice as _impl

__commandname__ = _impl.COMMAND_NAME


def RunCommand(is_interactive):
    result = _impl.send_to_slicer()
    return result if isinstance(result, Result) else Result.Success
