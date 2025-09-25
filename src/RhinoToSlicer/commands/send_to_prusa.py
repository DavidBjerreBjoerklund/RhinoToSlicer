"""Send selected Rhino geometry to PrusaSlicer.

This module provides helper functions that can be executed from Rhino's Python
script editor or bound to toolbar buttons. The main entry point is the
``send_to_prusaslicer`` function which exports the current selection to a
STEP file and launches PrusaSlicer with the exported model.

The module also defines the :class:`SendToPrusaCommand` class so the packaged
plug-in can register a real Rhino command that appears in the command line and
plug-in manager, matching Rhino's preferred Python plug-in structure.
"""
from __future__ import print_function

import json
import os
import subprocess
import tempfile
import uuid
from contextlib import contextmanager

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System
from Rhino.Commands import Result


_PRUSA_PATH_KEY = "RhinoToSlicer::PrusaPath"
_ENV_PATH_KEY = "PRUSA_SLICER_PATH"
_DEFAULT_EXTENSION = ".step"
_MAC_APP_SUFFIX = ".app"
_MAC_APP_EXECUTABLE = os.path.join("Contents", "MacOS", "PrusaSlicer")
_CONFIG_FILENAME = "send_to_prusa_config.json"
_COMMAND_NAME = "SendToPrusa"
_DEFAULT_MAC_APP_PATH = "/Applications/Original Prusa Drivers/PrusaSlicer.app"


def _is_windows():
    return System.Environment.OSVersion.Platform == System.PlatformID.Win32NT


def _is_macos():
    platform = System.Environment.OSVersion.Platform
    return platform == System.PlatformID.MacOSX or platform == System.PlatformID.Unix


def _normalize_prusa_path(path):
    if not path:
        return None
    path = os.path.expanduser(path)
    if _is_macos():
        lower = path.lower()
        if lower.endswith(_MAC_APP_SUFFIX):
            if os.path.isdir(path):
                app_binary = os.path.join(path, _MAC_APP_EXECUTABLE)
                if os.path.isfile(app_binary) or os.access(app_binary, os.X_OK):
                    return os.path.normpath(path)
            return None
        if os.path.isfile(path) or os.access(path, os.X_OK):
            return os.path.normpath(path)
        return None
    if os.path.isfile(path) or os.access(path, os.X_OK):
        return os.path.normpath(path)
    return None


def _config_path():
    try:
        base = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base = tempfile.gettempdir()
    return os.path.join(base, _CONFIG_FILENAME)


def _load_configured_path():
    config_path = _config_path()
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "rb") as handle:
            payload = json.load(handle)
    except (IOError, ValueError):
        return None
    configured = payload.get("prusa_path")
    return _normalize_prusa_path(configured) if configured else None


def _store_configured_path(path):
    config_path = _config_path()
    payload = json.dumps({"prusa_path": path}, indent=2)
    try:
        with open(config_path, "wb") as handle:
            handle.write(payload.encode("utf-8"))
    except IOError:
        print("Unable to persist the PrusaSlicer path next to the helper script.")


def _load_prusaslicer_path():
    env_path = os.environ.get(_ENV_PATH_KEY)
    env_path = _normalize_prusa_path(env_path) if env_path else None
    if env_path:
        sc.sticky[_PRUSA_PATH_KEY] = env_path
        return env_path

    config_path = _load_configured_path()
    if config_path:
        sc.sticky[_PRUSA_PATH_KEY] = config_path
        return config_path

    sticky_path = sc.sticky.get(_PRUSA_PATH_KEY)
    sticky_path = _normalize_prusa_path(sticky_path) if sticky_path else None
    if sticky_path:
        sc.sticky[_PRUSA_PATH_KEY] = sticky_path
        return sticky_path

    if _is_macos():
        default_path = _normalize_prusa_path(_DEFAULT_MAC_APP_PATH)
        if default_path:
            sc.sticky[_PRUSA_PATH_KEY] = default_path
            return default_path
    return None


def _prompt_for_prusaslicer():
    if _is_windows():
        filter_string = "PrusaSlicer executable (*.exe)|*.exe||"
    elif _is_macos():
        filter_string = "PrusaSlicer (*.app;PrusaSlicer)|*.app;PrusaSlicer||"
    else:
        filter_string = "Executable (*.*)|*.*||"

    path = rs.OpenFileName("Locate PrusaSlicer", filter_string)
    if not path:
        return None
    return _normalize_prusa_path(path)


def set_prusaslicer_path(path=None):
    """Persist the path to the PrusaSlicer executable.

    If *path* is omitted a file dialog is presented. The chosen path is stored
    in Rhino's sticky dictionary so that future calls can reuse it. The helper
    also respects the :data:`PRUSA_SLICER_PATH` environment variable.
    """
    if path:
        candidate = _normalize_prusa_path(path)
    else:
        candidate = _prompt_for_prusaslicer()
    if not candidate:
        print("PrusaSlicer path not set.")
        return None

    sc.sticky[_PRUSA_PATH_KEY] = candidate
    _store_configured_path(candidate)
    print("Stored PrusaSlicer path: {}".format(candidate))
    return candidate


@contextmanager
def _preserve_selection(new_selection):
    previous = rs.SelectedObjects() or []
    try:
        rs.UnselectAllObjects()
        if new_selection:
            rs.SelectObjects(list(new_selection))
        yield new_selection
    finally:
        rs.UnselectAllObjects()
        if previous:
            rs.SelectObjects(previous)


def _export_selection(temp_path):
    command_path = temp_path.replace("\\", "/")
    macro = "_-Export \"{}\" _Enter".format(command_path)
    if rs.Command(macro, echo=False):
        return os.path.exists(temp_path)
    return False


def _create_temp_export_path(extension=_DEFAULT_EXTENSION):
    filename = "RhinoToPrusa_{}{}".format(uuid.uuid4().hex, extension)
    return os.path.join(tempfile.gettempdir(), filename)


def _launch_prusaslicer(prusa_path, model_path):
    try:
        if _is_macos():
            lower = prusa_path.lower()
            if lower.endswith(_MAC_APP_SUFFIX):
                subprocess.Popen(["open", "-a", prusa_path, model_path])
                return
        subprocess.Popen([prusa_path, model_path])
    except OSError as exc:
        raise RuntimeError("Unable to start PrusaSlicer: {}".format(exc))


def send_to_prusaslicer():
    """Export the selected geometry to STEP and open it in PrusaSlicer."""
    objects = rs.GetObjects(
        "Select objects to send to PrusaSlicer",
        preselect=True,
        select=False,
        minimum_count=1,
    )
    if not objects:
        print("No geometry selected.")
        return Result.Cancel

    prusa_path = _load_prusaslicer_path()
    if not prusa_path:
        prusa_path = set_prusaslicer_path()
    if not prusa_path:
        return Result.Cancel

    export_path = _create_temp_export_path()

    with _preserve_selection(objects):
        success = _export_selection(export_path)
    if not success:
        if os.path.exists(export_path):
            try:
                os.remove(export_path)
            except OSError:
                pass
        print("Export failed. Check that the STEP exporter is installed and licensed.")
        return Result.Failure

    try:
        _launch_prusaslicer(prusa_path, export_path)
    except RuntimeError as exc:
        print(str(exc))
        return Result.Failure

    print("Exported {} objects to {} and launched PrusaSlicer.".format(len(objects), export_path))
    return Result.Success


class SendToPrusaCommand(Rhino.Commands.Command):
    """Rhino command wrapper that executes :func:`send_to_prusaslicer`."""

    def __init__(self):
        Rhino.Commands.Command.__init__(self)

    def EnglishName(self):  # noqa: N802 - Rhino API camelCase requirement
        return _COMMAND_NAME

    def RunCommand(self, doc, mode):  # noqa: N802 - Rhino API camelCase requirement
        result = send_to_prusaslicer()
        return result if isinstance(result, Result) else Result.Success


# Instantiate the command so Rhino registers it when the plug-in loads.
_command_instance = SendToPrusaCommand()


__commandname__ = _COMMAND_NAME


def RunCommand(is_interactive):
    return send_to_prusaslicer()


if __name__ == "__main__":
    send_to_prusaslicer()
