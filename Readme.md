# Rhino to PrusaSlicer bridge

This repository contains a Rhino CPython plug-in that exports the current
selection as a STEP file and opens it inside
[PrusaSlicer](https://www.prusa3d.com/page/prusaslicer_424/). Once installed, the
plug-in contributes the `SendToPrusa` command so a single click can send the
active model to the slicer.

## Features

- Rhino commands `SendToPrusa` (export and launch) and `SendToPrusaSetPath`
  (update the PrusaSlicer executable).
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
   The script locates your Rhino 8 user data folder (e.g.
   `%AppData%\McNeel\Rhinoceros\8.0` on Windows or
   `~/Library/Application Support/McNeel/Rhinoceros/8.0` on macOS), copies the
   plug-in files (`send_to_prusa.py`, `send_to_prusa_set_path.py`, and
   `__plugin__.py`) into `Plug-ins/PythonPlugIns/SendToPrusa`, and prompts for the PrusaSlicer
   executable. Pass `--prusa-path /absolute/path` for a non-interactive setup or
   `--no-prusa-config` to skip the prompt entirely. Use `--mode link` if you
   prefer a symlink for easier updates.
2. The installer also configures Rhino aliases named `SendToPrusa` and
   `SendToPrusaSetPath` that call the plug-in scripts via `RunPythonScript`.
   That makes the workflow available immediately—even if Rhino has not detected
   the plug-in yet—and you can wire those aliases to toolbar buttons or run
   them from Rhino's command line.
3. Rhino should detect the plug-in automatically at the next launch. If it
   doesn't, open _Rhino Options → Plug-ins → Python → Install…_ and select the
   `Plug-ins/PythonPlugIns/SendToPrusa` folder. The plug-in appears in the list
   as **RhinoToPrusa**.

### Manual install

If you prefer not to run the installer, copy `src/send_to_prusa.py`,
`src/send_to_prusa_set_path.py`, and `src/__plugin__.py` to your Rhino Python
plug-in directory (`%AppData%\McNeel\Rhinoceros\8.0\Plug-ins\PythonPlugIns\SendToPrusa`
or `~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/PythonPlugIns/SendToPrusa`).
Launch Rhino, ensure the plug-in is loaded, and run:
```
SendToPrusaSetPath
```
to store the PrusaSlicer path. The first execution of `SendToPrusa` registers
the matching Rhino alias so you can wire a toolbar button the same way as with
the installer. You can also add aliases manually with the macros below if you
skip the installer entirely:
```
! _-RunPythonScript ("/absolute/path/to/Plug-ins/PythonPlugIns/SendToPrusa/send_to_prusa.py")
! _-RunPythonScript ("/absolute/path/to/Plug-ins/PythonPlugIns/SendToPrusa/send_to_prusa_set_path.py")
```
Adjust the paths to match the location where you copied the scripts.

## Usage

1. Select the geometry you want to slice (or let the command prompt for it).
2. Run the `SendToPrusa` command (or click the toolbar button tied to the alias).
3. Rhino writes the selection to a temporary STEP file and starts PrusaSlicer
   with that file. The exported files remain in your temporary folder so you can
   reuse them if needed.

## Notes

- STEP export requires Rhino's standard STEP plug-in to be installed and
  licensed. If exporting fails, check the Rhino command line for details.
- On macOS, choose the `PrusaSlicer.app` bundle when prompted (or use the bundle
  path in `PRUSA_SLICER_PATH`). The plug-in uses the `open -a` helper so Rhino
  for Mac launches the application the same way Finder would.
- Linux builds of Rhino are not officially supported, but the plug-in will try
  to launch whichever executable path you provide.
- The installer stores configuration in `send_to_prusa_config.json` inside the
  plug-in folder so the slicer path persists across Rhino sessions.
