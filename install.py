#!/usr/bin/env python3
"""Installer utility for the Rhino ➜ PrusaSlicer bridge.

Running this script copies (or links) the Rhino helper into Rhino's scripts
folder so that ``RunPythonScript`` and toolbar buttons can import it. The
installer auto-detects the Rhino 8 user data directory on Windows and macOS,
but the target can be overridden via the command line.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

SCRIPT_NAME = "send_to_prusa.py"
CONFIG_FILENAME = "send_to_prusa_config.json"
ALIAS_NAME = "SendToPrusa"
ALIAS_MACRO = '! _-RunPythonScript ("import send_to_prusa; send_to_prusa.send_to_prusaslicer()")'
DEFAULT_VERSION = "8.0"


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


def _detect_rhino_scripts_dir(version: str) -> Path:
    return _detect_rhino_user_dir(version) / "scripts"


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


def _config_file_for(destination: Path) -> Path:
    return destination.with_name(CONFIG_FILENAME)


def _write_config(destination: Path, prusa_path: str, *, dry_run: bool) -> None:
    config_path = _config_file_for(destination)
    payload = {"prusa_path": prusa_path}
    if dry_run:
        print(f"Would store PrusaSlicer path in {config_path}")
        return
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Stored PrusaSlicer path in {config_path}")


def _load_existing_config(destination: Path) -> Optional[str]:
    config_path = _config_file_for(destination)
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    path = data.get("prusa_path")
    return _normalize_prusa_path(path) if path else None


def _configure_prusa_path(destination: Path, provided: Optional[str], *, dry_run: bool) -> None:
    normalized = _normalize_prusa_path(provided) if provided else None
    if provided and not normalized:
        print(f"Ignoring invalid PrusaSlicer path: {provided}")
    if not normalized:
        existing = _load_existing_config(destination)
        normalized = _prompt_for_prusa_path(existing)
    if not normalized:
        print("PrusaSlicer path not stored. You can run the installer again with --prusa-path.")
        return
    _write_config(destination, normalized, dry_run=dry_run)


def _alias_file(user_dir: Path) -> Path:
    return user_dir / "settings" / "aliases.txt"


def _ensure_alias(user_dir: Path, alias: str, macro: str, *, dry_run: bool) -> bool:
    alias_path = _alias_file(user_dir)
    alias_path.parent.mkdir(parents=True, exist_ok=True)
    existing_content = ""
    if alias_path.exists():
        try:
            existing_content = alias_path.read_text(encoding="utf-8")
        except OSError:
            print(f"Unable to read {alias_path}; skipping alias configuration.")
            return False
        lowered = existing_content.lstrip().lower()
        if lowered.startswith("<"):
            print(
                f"Alias file {alias_path} appears to be XML. Please add the alias manually in Rhino Options."
            )
            return False
        normalized_lines = [line.strip() for line in existing_content.replace("\r\n", "\n").split("\n")]
        for line in normalized_lines:
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if "=" not in line:
                continue
            name, _ = line.split("=", 1)
            if name.strip().lower() == alias.lower():
                print(f"Alias '{alias}' already configured in {alias_path}.")
                return True
    line = f"{alias}={macro}"
    if dry_run:
        print(f"Would append alias to {alias_path}: {line}")
        return True
    prefix = ""
    if alias_path.exists() and existing_content and not existing_content.endswith("\n"):
        prefix = "\n"
    try:
        with alias_path.open("a", encoding="utf-8") as stream:
            stream.write(prefix + line + "\n")
    except OSError as exc:
        print(f"Failed to update {alias_path}: {exc}")
        return False
    print(f"Added '{alias}' alias to {alias_path}.")
    return True


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
    parser.add_argument(
        "--alias-name",
        default=ALIAS_NAME,
        help="Name of the Rhino command alias to create (default: %(default)s).",
    )
    parser.add_argument(
        "--no-alias",
        action="store_true",
        help="Skip configuring the Rhino command alias.",
    )
    parser.set_defaults(configure_prusa=True)
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    if args.scripts_dir:
        scripts_dir = args.scripts_dir.expanduser().resolve()
        user_dir = scripts_dir.parent
    else:
        user_dir = _detect_rhino_user_dir(args.version)
        scripts_dir = user_dir / "scripts"

    print(f"Target Rhino scripts directory: {scripts_dir}")

    try:
        destination = install_plugin(scripts_dir=scripts_dir, mode=args.mode, dry_run=args.dry_run)
    except Exception as exc:  # pragma: no cover - installer level error
        print(f"Installation failed: {exc}")
        return 1

    configure_prusa = args.configure_prusa or bool(args.prusa_path)
    if configure_prusa:
        if args.dry_run and not args.prusa_path:
            print("Skipping PrusaSlicer path prompt during dry run.")
        else:
            _configure_prusa_path(destination, args.prusa_path, dry_run=args.dry_run)

    alias_configured = True
    if not args.no_alias:
        alias_configured = _ensure_alias(user_dir, args.alias_name, ALIAS_MACRO, dry_run=args.dry_run)

    if args.dry_run:
        print("Dry run complete. No files were modified.")
    else:
        print("Installation complete.")
        if args.no_alias:
            print(
                "Add a button or alias manually with:\n"
                "! _-RunPythonScript (\"import send_to_prusa; send_to_prusa.send_to_prusaslicer()\")"
            )
        elif alias_configured:
            print(
                f"Rhino alias '{args.alias_name}' now points at the helper. Use it directly or assign it to a toolbar button."
            )
        else:
            print(
                f"Unable to update Rhino's alias list automatically. Add '{args.alias_name}' manually with:\n"
                f"{ALIAS_MACRO}"
            )
    return 0


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    raise SystemExit(main())
