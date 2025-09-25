"""Send selected Rhino geometry to PrusaSlicer.

This module provides helper functions that can be executed from Rhino's Python
script editor or bound to toolbar buttons. The main entry point is the
``send_to_prusaslicer`` function which exports the current selection to a
STEP file and launches PrusaSlicer with the exported model.
"""

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


_PRUSA_PATH_KEY = "RhinoToSlicer::PrusaPath"
_ENV_PATH_KEY = "PRUSA_SLICER_PATH"
_DEFAULT_EXTENSION = ".step"
_MAC_APP_SUFFIX = ".app"
_MAC_APP_EXECUTABLE = os.path.join("Contents", "MacOS", "PrusaSlicer")
_CONFIG_FILENAME = "send_to_prusa_config.json"
_ALIAS_NAME = "SendToPrusa"
SET_PATH_COMMAND_NAME = "{}SetPath".format(_ALIAS_NAME)
_ALIAS_MACRO = '! _SendToPrusa'


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
        script_path = os.path.abspath(__file__)
    except (NameError, RuntimeError):  # pragma: no cover - fallback when __file__ missing
        return os.path.join(tempfile.gettempdir(), _CONFIG_FILENAME)
    return os.path.join(os.path.dirname(script_path), _CONFIG_FILENAME)


def _load_configured_path():
    config_path = _config_path()
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r") as stream:
            payload = json.load(stream)
    except (OSError, ValueError):
        return None
    configured = payload.get("prusa_path")
    return _normalize_prusa_path(configured) if configured else None


def _store_configured_path(path):
    config_path = _config_path()
    payload = json.dumps({"prusa_path": path}, indent=2)
    try:
        with open(config_path, "w") as stream:
            stream.write(payload)
    except OSError:
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
    options = Rhino.FileIO.FileWriteOptions()
    options.WriteSelectedObjectsOnly = True
    options.SuppressDialogBoxes = True
    if sc.doc.ExportSelected(temp_path, options):
        return os.path.exists(temp_path)
    return False


def _create_temp_export_path(extension=_DEFAULT_EXTENSION):
    filename = "RhinoToPrusa_{}{}".format(uuid.uuid4().hex, extension)
    return os.path.join(tempfile.gettempdir(), filename)


def _ensure_command_alias():
    macro = _ALIAS_MACRO
    try:
        alias_table = Rhino.ApplicationSettings.CommandAliases
    except AttributeError:
        alias_table = None
    if alias_table is not None:
        try:
            if alias_table.Contains(_ALIAS_NAME):
                existing = alias_table.GetMacro(_ALIAS_NAME)
                if existing == macro:
                    return
                print(
                    "Rhino alias '{}' already exists with a different macro; leaving it unchanged.".format(
                        _ALIAS_NAME
                    )
                )
                return
            if alias_table.Add(_ALIAS_NAME, macro):
                print("Registered Rhino alias '{}'".format(_ALIAS_NAME))
                return
            alias_table.SetMacro(_ALIAS_NAME, macro)
            print("Registered Rhino alias '{}'".format(_ALIAS_NAME))
            return
        except Exception:
            alias_table = None
    command = '-Alias "{}" "{}"'.format(_ALIAS_NAME, macro.replace('"', '""'))
    try:
        if Rhino.RhinoApp.RunScript(command, False):
            print("Registered Rhino alias '{}'".format(_ALIAS_NAME))
    except Exception:
        pass


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
    _ensure_command_alias()
    objects = rs.GetObjects(
        "Select objects to send to PrusaSlicer",
        preselect=True,
        select=False,
        minimum_count=1,
    )
    if not objects:
        print("No geometry selected.")
        return Rhino.Commands.Result.Cancel

    prusa_path = _load_prusaslicer_path()
    if not prusa_path:
        prusa_path = set_prusaslicer_path()
    if not prusa_path:
        return Rhino.Commands.Result.Cancel

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
        return Rhino.Commands.Result.Failure

    try:
        _launch_prusaslicer(prusa_path, export_path)
    except RuntimeError as exc:
        print(str(exc))
        return Rhino.Commands.Result.Failure

    print("Exported {} objects to {} and launched PrusaSlicer.".format(len(objects), export_path))
    return Rhino.Commands.Result.Success


__commandname__ = _ALIAS_NAME


def RunCommand(is_interactive):
    return send_to_prusaslicer()


if __name__ == "__main__":
    send_to_prusaslicer()
