"""Rhino command shim that delegates to the RhinoToSlicer helper module."""

from __future__ import print_function

from Rhino.Commands import Result

from RhinoToSlicer.commands import send_to_prusa as _impl

__commandname__ = _impl.COMMAND_NAME


def RunCommand(is_interactive):
    result = _impl.send_to_prusaslicer()
    return result if isinstance(result, Result) else Result.Success
