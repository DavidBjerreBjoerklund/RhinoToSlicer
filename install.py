#!/usr/bin/env python3
"""Installer utility for the Rhino ➜ PrusaSlicer bridge.

Running this script copies (or links) the packaged Rhino Python plug-in into
Rhino's ``PythonPlugIns`` directory so the ``SendToPrusa`` command appears in
the plug-in manager. The installer auto-detects the Rhino 8 user data
directory on Windows and macOS, but the target can be overridden via the
command line.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
SRC_ROOT = HERE / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from RhinoToSlicer import PLUGIN_ID  # noqa: E402 - imported after sys.path tweak

PLUGIN_DIRNAME = "RhinoToSlicer {{{}}}".format(PLUGIN_ID)
DEV_SOURCE = SRC_ROOT / "RhinoToSlicer"
CONFIG_FILENAME = "send_to_prusa_config.json"
DEFAULT_VERSION = "8.0"
_DEFAULT_MAC_PRUSA_PATH = "/Applications/Original Prusa Drivers/PrusaSlicer.app"


def _detect_rhino_user_dir(version: str) -> Path:
    """Locate Rhino's per-user data directory for the given version."""

    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
        return base / "McNeel" / "Rhinoceros" / version

    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "McNeel" / "Rhinoceros"
        return base / version

    # Rhino 8 is only supported on Windows and macOS, but fall back to a
    # reasonable XDG location so the installer still works in testing setups.
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "McNeel" / "Rhinoceros" / version


def _detect_rhino_python_plugin_dir(version: str) -> Path:
    return _detect_rhino_user_dir(version) / "Plug-ins" / "PythonPlugIns"


def _normalize_prusa_path(path: str) -> Optional[str]:
    path = os.path.expanduser(path)
    if not path:
        return None
    if sys.platform == "darwin":
        lower = path.lower()
        if lower.endswith(".app"):
            bundle_binary = os.path.join(path, "Contents", "MacOS", "PrusaSlicer")
            if os.path.isdir(path) and (os.path.isfile(bundle_binary) or os.access(bundle_binary, os.X_OK)):
                return os.path.normpath(path)
            return None
    if os.path.isfile(path) or os.access(path, os.X_OK):
        return os.path.normpath(path)
    return None


def _prompt_for_prusa_path(existing: Optional[str]) -> Optional[str]:
    hint = f" [{existing}]" if existing else ""
    response = input(f"Path to PrusaSlicer executable or app{hint}: ").strip()
    if not response:
        return existing
    normalized = _normalize_prusa_path(response)
    if not normalized:
        print("Provided path is not executable. Please verify and re-run.")
    return normalized


def _config_file_for(plugin_root: Path) -> Path:
    return plugin_root / CONFIG_FILENAME


def _write_config(plugin_root: Path, prusa_path: str, *, dry_run: bool) -> None:
    config_path = _config_file_for(plugin_root)
    if not dry_run:
        config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"prusa_path": prusa_path}
    if dry_run:
        print(f"Would store PrusaSlicer path in {config_path}")
        return
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Stored PrusaSlicer path in {config_path}")


def _load_existing_config(plugin_root: Path) -> Optional[str]:
    config_path = _config_file_for(plugin_root)
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    path = data.get("prusa_path")
    return _normalize_prusa_path(path) if path else None


def _configure_prusa_path(plugin_root: Path, provided: Optional[str], *, dry_run: bool) -> None:
    normalized = _normalize_prusa_path(provided) if provided else None
    if provided and not normalized:
        print(f"Ignoring invalid PrusaSlicer path: {provided}")
    if not normalized:
        existing = _load_existing_config(plugin_root)
        if not existing and sys.platform == "darwin":
            existing = _normalize_prusa_path(_DEFAULT_MAC_PRUSA_PATH)
        normalized = _prompt_for_prusa_path(existing)
    if not normalized:
        print("PrusaSlicer path not stored. You can run the installer again with --prusa-path.")
        return
    _write_config(plugin_root, normalized, dry_run=dry_run)


def _remove_existing(path: Path, *, dry_run: bool) -> None:
    if not (path.exists() or path.is_symlink()):
        return
    if dry_run:
        print(f"Would remove existing {path}.")
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
    print(f"Removed existing {path}.")


def install_plugin(*, plugin_dir: Path, mode: str, dry_run: bool) -> Path:
    source = DEV_SOURCE
    if not source.exists():
        raise FileNotFoundError("Unable to locate dev files next to the installer")

    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_root = plugin_dir / PLUGIN_DIRNAME

    _remove_existing(plugin_root, dry_run=dry_run)

    if dry_run:
        print(f"Would {mode} {source} -> {plugin_root}")
        return plugin_root

    if mode == "copy":
        shutil.copytree(source, plugin_root)
    else:
        plugin_root.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            target = plugin_root / item.name
            if target.exists() or target.is_symlink():
                if target.is_dir() and not target.is_symlink():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            if item.is_dir():
                target.symlink_to(item, target_is_directory=True)
            else:
                target.symlink_to(item)
    print(f"Installed {plugin_root} ({mode}).")
    return plugin_root


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the RhinoToSlicer helper into Rhino 8.")
    parser.add_argument(
        "--scripts-dir",
        type=Path,
        help="[deprecated] Override the Rhino scripts directory used by older installs.",
    )
    parser.add_argument(
        "--plugins-dir",
        type=Path,
        help="Override the Rhino Python plug-in directory. Defaults to the Rhino 8 user folder for the current OS.",
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
    parser.add_argument(
        "--no-prusa-config",
        dest="configure_prusa",
        action="store_false",
        help="Skip prompting for the PrusaSlicer executable during installation.",
    )
    parser.add_argument(
        "--prusa-path",
        help="Set the PrusaSlicer executable path non-interactively (overrides the interactive prompt).",
    )
    parser.set_defaults(configure_prusa=True)
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    if args.scripts_dir:
        print(
            "--scripts-dir is deprecated for the packaged plug-in installer. Use --plugins-dir instead."
        )
        plugin_dir = args.scripts_dir.expanduser().resolve()
        user_dir = plugin_dir.parent
    elif getattr(args, "plugins_dir", None):
        plugin_dir = args.plugins_dir.expanduser().resolve()
        user_dir = plugin_dir.parent
    else:
        user_dir = _detect_rhino_user_dir(args.version)
        plugin_dir = _detect_rhino_python_plugin_dir(args.version)

    print(f"Target Rhino Python plug-in directory: {plugin_dir}")

    try:
        plugin_root = install_plugin(plugin_dir=plugin_dir, mode=args.mode, dry_run=args.dry_run)
    except Exception as exc:  # pragma: no cover - installer level error
        print(f"Installation failed: {exc}")
        return 1

    configure_prusa = args.configure_prusa or bool(args.prusa_path)
    if configure_prusa:
        if args.dry_run and not args.prusa_path:
            print("Skipping PrusaSlicer path prompt during dry run.")
        else:
            _configure_prusa_path(plugin_root, args.prusa_path, dry_run=args.dry_run)

    if args.dry_run:
        print("Dry run complete. No files were modified.")
    else:
        print("Installation complete.")
        print(
            "Launch Rhino and enable the RhinoToSlicer plug-in under Tools → Options → Plug-ins if it is not loaded automatically."
        )
        print("Run the SendToPrusa command to send geometry to PrusaSlicer.")
    return 0


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    raise SystemExit(main())
