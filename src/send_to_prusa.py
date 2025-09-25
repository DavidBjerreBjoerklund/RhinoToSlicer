"""Compatibility wrapper for legacy installs.

This module proxies to the packaged RhinoToSlicer plug-in so that existing
macros using ``import send_to_prusa`` continue to function whether they run
inside Rhino or directly from this repository.
"""

from __future__ import print_function

import os
import sys


_HERE = os.path.dirname(os.path.abspath(__file__))
_DEV_ROOT = os.path.join(_HERE, "plugin", "dev")

if os.path.isdir(_DEV_ROOT) and _DEV_ROOT not in sys.path:
    sys.path.insert(0, _DEV_ROOT)

try:
    from RhinoToSlicer.commands.send_to_prusa import *  # noqa: F401,F403
except ImportError as exc:  # pragma: no cover - helpful error when running outside Rhino
    print("Unable to import RhinoToSlicer helpers: {}".format(exc))
    raise
