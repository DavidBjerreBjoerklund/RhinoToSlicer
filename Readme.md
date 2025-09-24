# Rhino to PrusaSlicer bridge

This repository contains a small Rhino Python helper that exports the current
selection as a STEP file and opens it inside [PrusaSlicer](https://www.prusa3d.com/page/prusaslicer_424/).
It is intended to be attached to a toolbar button so that a single click sends
the active model to the slicer.

## Features

- Prompts for geometry if nothing is pre-selected.
- Remembers the PrusaSlicer executable path using Rhino's sticky dictionary or
  the `PRUSA_SLICER_PATH` environment variable.
- Exports selected objects to a temporary `.step` file using Rhino's native
  exporter.
- Launches PrusaSlicer with the exported file as an argument.

## Installation

### Quick installer (Rhino 8)

1. Run the installer from a terminal:
   ```
   python3 install.py
   ```
   The script locates your Rhino 8 *scripts* directory (e.g.
   `%AppData%\McNeel\Rhinoceros\8.0\scripts` on Windows or
   `~/Library/Application Support/McNeel/Rhinoceros/8.0/scripts` on macOS),
   copies `send_to_prusa.py` there, and prompts for the PrusaSlicer executable.
   The chosen path is stored next to the helper so future runs know where to
   launch the slicer. Pass `--prusa-path /absolute/path` if you prefer a
   non-interactive setup or `--no-prusa-config` to skip the prompt entirely.
   Use `--mode link` if you prefer a symlink for easier updates.
2. The installer also configures a Rhino command alias named `SendToPrusa`. You
   can trigger the helper by typing that command, assigning it to a toolbar
   button, or calling it from macros. For example, set a button's left click to
   `SendToPrusa` and the right click to:
   ```
   ! _-RunPythonScript ("import send_to_prusa; send_to_prusa.set_prusaslicer_path()")
   ```

### Manual install

If you prefer not to run the installer, copy `src/send_to_prusa.py` to your
Rhino scripts directory manually (`%AppData%\McNeel\Rhinoceros\8.0\scripts`
or `~/Library/Application Support/McNeel/Rhinoceros/8.0/scripts`). Launch Rhino
and run:
```
_-RunPythonScript ("import send_to_prusa; send_to_prusa.set_prusaslicer_path()")
```
to store the PrusaSlicer path. The first execution of
`send_to_prusa.send_to_prusaslicer()` (or the `SendToPrusa` command) will add the
matching Rhino alias so you can wire a toolbar button the same way as with the
installer.

## Usage

1. Select the geometry you want to slice.
2. Click the toolbar button or run the `SendToPrusa` command/alias configured
   during installation.
3. Rhino writes the selection to a temporary STEP file and starts PrusaSlicer
   with that file. The exported files are left in your temporary folder so you
   can reuse them if needed.

## Notes

- STEP export requires Rhino's standard STEP plug-in to be installed and
  licensed. If exporting fails, check the Rhino command line for details.
- On macOS, choose the `PrusaSlicer.app` bundle when prompted (or use the
  bundle path in `PRUSA_SLICER_PATH`). The script uses the `open -a` helper so
  that Rhino for Mac launches the application the same way Finder would.
- Linux builds of Rhino are not officially supported, but the script will try
  to launch whichever executable path you provide.
- The installer stores configuration in `send_to_prusa_config.json` next to the
  helper script so that the slicer path persists across Rhino sessions.
