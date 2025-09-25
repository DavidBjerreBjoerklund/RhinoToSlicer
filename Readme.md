# Rhino to PrusaSlicer bridge

This repository contains a packaged Rhino Python plug-in that exports the
current selection as a STEP file and opens it inside
[PrusaSlicer](https://www.prusa3d.com/page/prusaslicer_424/). Once installed,
the plug-in adds a `SendToPrusa` command to Rhino so a single click can send
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
   The script locates your Rhino 8 *Python plug-ins* directory (e.g.
   `%AppData%\McNeel\Rhinoceros\8.0\Plug-ins\PythonPlugIns` on Windows or
   `~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/PythonPlugIns`
   on macOS), copies the packaged plug-in there, and prompts for the
  PrusaSlicer executable. The chosen path is stored inside the plug-in's
  `dev` folder so future runs know where to launch the slicer from. Pass
  `--prusa-path /absolute/path` if you prefer a non-interactive setup or
  `--no-prusa-config` to skip the prompt entirely. Use `--mode link` if you
  prefer a symlink for easier updates.
2. Start Rhino, open **Tools → Options → Plug-ins**, and ensure the
   *RhinoToSlicer* plug-in is enabled. You can now trigger the helper by typing
   the `SendToPrusa` command, binding it to a toolbar button, or calling it from
   macros. On first launch Rhino may need to load Python support before the
   command appears; running `EditPythonScript` once forces Rhino to refresh the
   plug-in cache.

### Manual install

If you prefer not to run the installer, create a folder named
`RhinoToSlicer {2e965250-8f1e-4e55-8b02-01c0924325b8}` in your Rhino Python
plug-ins directory ( `%AppData%\McNeel\Rhinoceros\8.0\Plug-ins\PythonPlugIns`
on Windows or
`~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/PythonPlugIns`
on macOS). Copy the contents of `src/plugin/` into that folder so Rhino sees
the expected `dev` subdirectory. Launch Rhino, enable the plug-in if necessary,
and run the `SendToPrusa` command once to store the PrusaSlicer path.

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
- On macOS, the installer defaults to
  `/Applications/Original Prusa Drivers/PrusaSlicer.app`. Choose that bundle
  when prompted (or set the path via `PRUSA_SLICER_PATH`). The plug-in uses the
  `open -a` helper so Rhino for Mac launches the application the same way
  Finder would.
- Linux builds of Rhino are not officially supported, but the script will try
  to launch whichever executable path you provide.
- The installer stores configuration in `send_to_prusa_config.json` inside the
  plug-in folder so that the slicer path persists across Rhino sessions.
