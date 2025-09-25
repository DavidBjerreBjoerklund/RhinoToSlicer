#!/usr/bin/env python
"""Installer utility for the Rhino to PrusaSlicer bridge."""

from __future__ import print_function

import argparse
import io
import json
import os
import shutil
import sys

SCRIPT_NAME = "send_to_prusa.py"
SET_PATH_SCRIPT_NAME = "send_to_prusa_set_path.py"
PLUGIN_ENTRY_NAME = "__plugin__.py"
PLUGIN_DIR_NAME = "SendToPrusa"
CONFIG_FILENAME = "send_to_prusa_config.json"
ALIAS_NAME = "SendToPrusa"
DEFAULT_VERSION = "8.0"

try:
    input_function = raw_input  # type: ignore[name-defined]
except NameError:  # pragma: no cover - Python 3 fallback for local testing
    input_function = input


def _detect_rhino_user_dir(version):
    """Locate Rhino's per-user data directory for the given version."""

    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = appdata
        else:
            base = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        return os.path.join(base, "McNeel", "Rhinoceros", version)

    if sys.platform == "darwin":
        base = os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", "McNeel", "Rhinoceros"
        )
        return os.path.join(base, version)

    base = os.environ.get(
        "XDG_DATA_HOME",
        os.path.join(os.path.expanduser("~"), ".local", "share"),
    )
    return os.path.join(base, "McNeel", "Rhinoceros", version)


def _detect_plugin_dir(user_dir):
    return os.path.join(user_dir, "Plug-ins", "PythonPlugIns", PLUGIN_DIR_NAME)


def _ensure_directory(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except OSError:
            if not os.path.isdir(path):
                raise


def _normalize_prusa_path(path):
    if not path:
        return None
    path = os.path.expanduser(path)
    if sys.platform == "darwin":
        lower = path.lower()
        if lower.endswith(".app"):
            bundle_binary = os.path.join(path, "Contents", "MacOS", "PrusaSlicer")
            if os.path.isdir(path) and (
                os.path.isfile(bundle_binary) or os.access(bundle_binary, os.X_OK)
            ):
                return os.path.normpath(path)
            return None
    if os.path.isfile(path) or os.access(path, os.X_OK):
        return os.path.normpath(path)
    return None


def _prompt_for_prusa_path(existing):
    if existing:
        hint = " [{}]".format(existing)
    else:
        hint = ""
    response = input_function("Path to PrusaSlicer executable or app{}: ".format(hint)).strip()
    if not response:
        return existing
    normalized = _normalize_prusa_path(response)
    if not normalized:
        print("Provided path is not executable. Please verify and re-run.")
    return normalized


def _config_file_for(script_path):
    return os.path.join(os.path.dirname(script_path), CONFIG_FILENAME)


def _write_config(script_path, prusa_path, dry_run):
    config_path = _config_file_for(script_path)
    if dry_run:
        print("Would store PrusaSlicer path in {}".format(config_path))
        return
    payload = json.dumps({"prusa_path": prusa_path}, indent=2)
    with io.open(config_path, "w", encoding="utf-8") as stream:
        stream.write(payload)
    print("Stored PrusaSlicer path in {}".format(config_path))


def _load_existing_config(script_path):
    config_path = _config_file_for(script_path)
    if not os.path.exists(config_path):
        return None
    try:
        with io.open(config_path, "r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (IOError, ValueError):
        return None
    path = data.get("prusa_path")
    if not path:
        return None
    return _normalize_prusa_path(path)


def _configure_prusa_path(script_path, provided, dry_run):
    normalized = _normalize_prusa_path(provided) if provided else None
    if provided and not normalized:
        print("Ignoring invalid PrusaSlicer path: {}".format(provided))
    if not normalized:
        existing = _load_existing_config(script_path)
        normalized = _prompt_for_prusa_path(existing)
    if not normalized:
        print("PrusaSlicer path not stored. You can run the installer again with --prusa-path.")
        return
    _write_config(script_path, normalized, dry_run)


def _alias_file(user_dir):
    return os.path.join(user_dir, "settings", "aliases.txt")


def _build_run_python_macro(script_path):
    normalized = script_path.replace("\\", "/")
    return '! _-RunPythonScript ("{}")'.format(normalized)


def _ensure_alias(user_dir, alias, macro, dry_run):
    alias_path = _alias_file(user_dir)
    alias_dir = os.path.dirname(alias_path)
    _ensure_directory(alias_dir)
    existing_content = ""
    if os.path.exists(alias_path):
        try:
            with io.open(alias_path, "r", encoding="utf-8") as stream:
                existing_content = stream.read()
        except IOError:
            print("Unable to read {}; skipping alias configuration.".format(alias_path))
            return False
        lowered = existing_content.lstrip().lower()
        if lowered.startswith("<"):
            print(
                "Alias file {} appears to be XML. Please add the alias manually in Rhino Options.".format(
                    alias_path
                )
            )
            return False
        normalized_lines = [
            line.strip() for line in existing_content.replace("\r\n", "\n").split("\n")
        ]
        for line in normalized_lines:
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if "=" not in line:
                continue
            name, _ = line.split("=", 1)
            if name.strip().lower() == alias.lower():
                print("Alias '{}' already configured in {}.".format(alias, alias_path))
                return True
    line = "{}={}".format(alias, macro)
    if dry_run:
        print("Would append alias to {}: {}".format(alias_path, line))
        return True
    prefix = ""
    if existing_content and not existing_content.endswith("\n"):
        prefix = "\n"
    try:
        with io.open(alias_path, "a", encoding="utf-8") as stream:
            stream.write(prefix + line + "\n")
    except IOError as exc:
        print("Failed to update {}: {}".format(alias_path, exc))
        return False
    print("Added '{}' alias to {}.".format(alias, alias_path))
    return True


def _copy_or_link(source, destination, mode, dry_run):
    if os.path.lexists(destination):
        if dry_run:
            action = "would replace"
        else:
            if os.path.isdir(destination) and not os.path.islink(destination):
                raise RuntimeError("Destination {} is a directory, aborting".format(destination))
            os.unlink(destination)
            action = "replaced"
        print("Existing {} {}.".format(destination, action))
    if dry_run:
        print("Would {} {} -> {}".format(mode, source, destination))
        return
    if mode == "copy":
        shutil.copy2(source, destination)
    else:
        os.symlink(source, destination)
    print("Installed {} ({}).".format(destination, mode))


def install_plugin_bundle(plugin_dir, mode, dry_run):
    source_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
    _ensure_directory(plugin_dir)
    installed = {}
    for filename in (SCRIPT_NAME, SET_PATH_SCRIPT_NAME, PLUGIN_ENTRY_NAME):
        source = os.path.join(source_root, filename)
        if not os.path.exists(source):
            raise IOError("Unable to locate {} next to the installer".format(filename))
        destination = os.path.join(plugin_dir, filename)
        _copy_or_link(source, destination, mode=mode, dry_run=dry_run)
        installed[filename] = destination
    return installed


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Install the RhinoToSlicer plug-in into Rhino 8."
    )
    parser.add_argument(
        "--scripts-dir",
        help="Override the Rhino scripts directory (used to locate the user profile). Defaults to the Rhino 8 user folder.",
    )
    parser.add_argument(
        "--plugin-dir",
        help="Override the target Python plug-in directory.",
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
        help="Install mode: copy the files (default) or create symlinks for easier updates.",
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


def main(argv=None):
    args = parse_args(argv)

    if args.scripts_dir:
        scripts_dir = os.path.abspath(os.path.expanduser(args.scripts_dir))
        user_dir = os.path.dirname(scripts_dir)
    else:
        user_dir = _detect_rhino_user_dir(args.version)

    if args.plugin_dir:
        plugin_dir = os.path.abspath(os.path.expanduser(args.plugin_dir))
    else:
        plugin_dir = _detect_plugin_dir(user_dir)

    print("Target Rhino plug-in directory: {}".format(plugin_dir))

    try:
        installed_files = install_plugin_bundle(
            plugin_dir=plugin_dir, mode=args.mode, dry_run=args.dry_run
        )
    except Exception as exc:
        print("Installation failed: {}".format(exc))
        return 1

    send_script = installed_files[SCRIPT_NAME]
    configure_script = installed_files[SET_PATH_SCRIPT_NAME]

    configure_prusa = args.configure_prusa or bool(args.prusa_path)
    if configure_prusa:
        if args.dry_run and not args.prusa_path:
            print("Skipping PrusaSlicer path prompt during dry run.")
        else:
            _configure_prusa_path(send_script, args.prusa_path, dry_run=args.dry_run)

    alias_results = []
    if not args.no_alias:
        send_macro = _build_run_python_macro(send_script)
        alias_results.append(
            _ensure_alias(user_dir, args.alias_name, send_macro, dry_run=args.dry_run)
        )
        configure_alias = "{}SetPath".format(args.alias_name)
        configure_macro = _build_run_python_macro(configure_script)
        alias_results.append(
            _ensure_alias(user_dir, configure_alias, configure_macro, dry_run=args.dry_run)
        )
    else:
        configure_alias = "{}SetPath".format(args.alias_name)

    alias_configured = all(alias_results) if alias_results else True

    if args.dry_run:
        print("Dry run complete. No files were modified.")
    else:
        print("Installation complete.")
        if args.no_alias:
            print(
                "Add toolbar buttons or aliases manually with:\n"
                "! _-RunPythonScript (\"{}\")\n"
                "! _-RunPythonScript (\"{}\")".format(
                    send_script.replace("\\", "/"),
                    configure_script.replace("\\", "/"),
                )
            )
        elif alias_configured:
            print(
                "Rhino aliases '{}' and '{}' now execute the plug-in scripts.".format(
                    args.alias_name, configure_alias
                )
            )
        else:
            print(
                "Unable to update Rhino's alias list automatically. Add the following manually:\n"
                "{}\n{}".format(send_macro, configure_macro)
            )
        print(
            "Load the plug-in from Rhino's Plug-in manager if it isn't detected automatically and run 'SendToPrusaSetPath' to update the slicer path."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
