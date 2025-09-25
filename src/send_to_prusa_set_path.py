"""Rhino command shim that updates the PrusaSlicer executable path."""

import Rhino

import send_to_prusa


__commandname__ = send_to_prusa.SET_PATH_COMMAND_NAME


def RunCommand(is_interactive):  # pragma: no cover - Rhino callback
    path = send_to_prusa.set_prusaslicer_path()
    return Rhino.Commands.Result.Success if path else Rhino.Commands.Result.Cancel


if __name__ == "__main__":  # pragma: no cover - convenience entry point
    RunCommand(True)
