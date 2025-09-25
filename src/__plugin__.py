"""Rhino CPython plug-in entry point for the Rhino ➜ PrusaSlicer bridge."""

import os
import sys

import Rhino
import System

# Ensure the helper module that performs the heavy lifting is importable. When
# Rhino loads the plug-in it executes this module from the plug-in folder,
# which also contains ``send_to_prusa.py``. Some Rhino configurations do not
# automatically append that folder to ``sys.path`` when running CPython plug-ins,
# so add it explicitly to keep imports reliable.
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

import send_to_prusa  # noqa: E402  # pylint: disable=wrong-import-position

__plugin_id__ = "4f0b3a66-0b2e-49fa-8ae2-2b3f707ceba9"
__plugin_name__ = "RhinoToPrusa"
__plugin_version__ = "0.3.0"
__plugin_description__ = "Export selected Rhino geometry to PrusaSlicer."

_PLUGIN_GUID = System.Guid(__plugin_id__)
_SEND_ALIAS = send_to_prusa._ALIAS_NAME  # reuse the shared command name
_CONFIGURE_COMMAND = send_to_prusa.SET_PATH_COMMAND_NAME


class RhinoToPrusaPlugIn(Rhino.PlugIns.PlugIn):
    """Minimal plug-in that exposes the Prusa commands in Rhino."""

    instance = None

    def __init__(self):
        super().__init__()
        RhinoToPrusaPlugIn.instance = self

    @property
    def Id(self):  # pragma: no cover - Rhino callback
        return _PLUGIN_GUID

    @property
    def PlugInName(self):  # pragma: no cover - Rhino callback
        return __plugin_name__

    @property
    def Version(self):  # pragma: no cover - Rhino callback
        return __plugin_version__

    def OnLoadPlugIn(self):  # pragma: no cover
        # Register the alias so the command also appears in Rhino's alias list.
        send_to_prusa._ensure_command_alias()
        return Rhino.PlugIns.LoadReturnCode.Success


class SendToPrusaCommand(Rhino.Commands.Command):
    """Expose ``SendToPrusa`` as a Rhino command."""

    instance = None

    def __init__(self):
        super().__init__()
        SendToPrusaCommand.instance = self

    def EnglishName(self):  # pragma: no cover - Rhino callback
        return _SEND_ALIAS

    def RunCommand(  # pragma: no cover - Rhino callback
        self, doc, mode
    ):
        return send_to_prusa.send_to_prusaslicer()


class ConfigurePrusaPathCommand(Rhino.Commands.Command):
    """Expose ``SendToPrusaSetPath`` to update the slicer executable."""

    instance = None

    def __init__(self):
        super().__init__()
        ConfigurePrusaPathCommand.instance = self

    def EnglishName(self):  # pragma: no cover - Rhino callback
        return _CONFIGURE_COMMAND

    def RunCommand(  # pragma: no cover - Rhino callback
        self, doc, mode
    ):
        path = send_to_prusa.set_prusaslicer_path()
        return Rhino.Commands.Result.Success if path else Rhino.Commands.Result.Cancel


# Instantiate the commands so Rhino registers them when the plug-in loads.
RhinoToPrusaPlugIn()
SendToPrusaCommand()
ConfigurePrusaPathCommand()
