"""Plug-in manifest for the RhinoToSlicer Python plug-in."""
from __future__ import annotations

from . import __version__


_PLUGIN_ID = "2e965250-8f1e-4e55-8b02-01c0924325b8"
_COMMAND_ID = "4d132b17-6c16-4d2e-9835-4e6ef8c7207b"


def PlugInInfo() -> dict[str, object]:
    """Return Rhino plug-in metadata consumed by Rhino's Python plug-in loader."""

    return {
        "Name": "RhinoToSlicer",
        "Id": _PLUGIN_ID,
        "Version": __version__,
        "Description": "Export Rhino geometry to PrusaSlicer.",
        "DeveloperName": "RhinoToSlicer",
        "Commands": [
            {
                "Name": "SendToPrusa",
                "EnglishName": "SendToPrusa",
                "Id": _COMMAND_ID,
                "File": "commands/send_to_prusa.py",
            }
        ],
    }
