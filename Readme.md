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
   `~/Library/Application Support/McNeel/Rhinoceros/8.0/scripts` on macOS) and
   copies `send_to_prusa.py` there. Use `--mode link` if you prefer a symlink
   for easier updates.
2. (Optional) Set the `PRUSA_SLICER_PATH` environment variable to the absolute
   path of the PrusaSlicer executable. If not set, the script will prompt for
   the location the first time it runs and remember it for subsequent sessions.
   On macOS you can point the variable at the `.app` bundle itself, e.g.
   `export PRUSA_SLICER_PATH="/Applications/PrusaSlicer.app"`.
3. Create a toolbar button or alias that runs the script:
   ```
   ! _-RunPythonScript ("import send_to_prusa; send_to_prusa.send_to_prusaslicer()")
   ```
   For convenience you can assign the right-click action of the same button to
   configure the PrusaSlicer path:
   ```
   ! _-RunPythonScript ("import send_to_prusa; send_to_prusa.set_prusaslicer_path()")
   ```

### Manual install

If you prefer not to run the installer, copy `src/send_to_prusa.py` to your
Rhino scripts directory manually (`%AppData%\McNeel\Rhinoceros\8.0\scripts`
or `~/Library/Application Support/McNeel/Rhinoceros/8.0/scripts`). Afterwards
follow steps 2 and 3 above.

## Usage

1. Select the geometry you want to slice.
2. Click the toolbar button or run the alias configured above.
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
