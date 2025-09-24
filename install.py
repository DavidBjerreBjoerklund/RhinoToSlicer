#!/usr/bin/env python3
"""Installer utility for the Rhino ➜ PrusaSlicer bridge.

Running this script copies (or links) the Rhino helper into Rhino's scripts
folder so that ``RunPythonScript`` and toolbar buttons can import it. The
installer auto-detects the Rhino 8 user data directory on Windows and macOS,
but the target can be overridden via the command line.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

SCRIPT_NAME = "send_to_prusa.py"
DEFAULT_VERSION = "8.0"


def _detect_rhino_scripts_dir(version: str) -> Path:
    """Best-effort detection of the Rhino scripts directory.

    Parameters
    ----------
    version:
        Rhino user folder version (e.g. ``"8.0"``).
    """

    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
        return base / "McNeel" / "Rhinoceros" / version / "scripts"

    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "McNeel" / "Rhinoceros"
        return base / version / "scripts"

    # Rhino 8 is only supported on Windows and macOS, but fall back to a
    # reasonable XDG location so the installer still works in testing setups.
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "McNeel" / "Rhinoceros" / version / "scripts"


def _copy_or_link(source: Path, destination: Path, *, mode: str, dry_run: bool) -> None:
    if destination.exists() or destination.is_symlink():
        if dry_run:
            action = "would replace"
        else:
            if destination.is_dir() and not destination.is_symlink():
                raise RuntimeError(f"Destination {destination} is a directory, aborting")
            destination.unlink()
            action = "replaced"
        print(f"Existing {destination} {action}.")

    if dry_run:
        print(f"Would {mode} {source} -> {destination}")
        return

    if mode == "copy":
        shutil.copy2(source, destination)
    else:
        destination.symlink_to(source)

    print(f"Installed {destination} ({mode}).")


def install_plugin(*, scripts_dir: Path, mode: str, dry_run: bool) -> Path:
    source = Path(__file__).resolve().parent / "src" / SCRIPT_NAME
    if not source.exists():
        raise FileNotFoundError(f"Unable to locate {SCRIPT_NAME} next to the installer")

    scripts_dir.mkdir(parents=True, exist_ok=True)
    destination = scripts_dir / SCRIPT_NAME
    _copy_or_link(source, destination, mode=mode, dry_run=dry_run)
    return destination


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the RhinoToSlicer helper into Rhino 8.")
    parser.add_argument(
        "--scripts-dir",
        type=Path,
        help="Override the Rhino scripts directory. Defaults to the Rhino 8 user folder for the current OS.",
    )
    parser.add_argument(
        "--version",
        default=DEFAULT_VERSION,
        help="Rhino user folder version (default: %(default)s).",
    )
    parser.add_argument(
        "--mode",
        choices=("copy", "link"),
        default="copy",
        help="Install mode: copy the script (default) or create a symlink for easier updates.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without touching the filesystem.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    if args.scripts_dir:
        scripts_dir = args.scripts_dir.expanduser().resolve()
    else:
        scripts_dir = _detect_rhino_scripts_dir(args.version)

    print(f"Target Rhino scripts directory: {scripts_dir}")

    try:
        destination = install_plugin(scripts_dir=scripts_dir, mode=args.mode, dry_run=args.dry_run)
    except Exception as exc:  # pragma: no cover - installer level error
        print(f"Installation failed: {exc}")
        return 1

    if args.dry_run:
        print("Dry run complete. No files were modified.")
    else:
        print("Installation complete.")
        print(
            "In Rhino, create a button or alias with:\n"
            "! _-RunPythonScript (\"import send_to_prusa; send_to_prusa.send_to_prusaslicer()\")"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    raise SystemExit(main())
