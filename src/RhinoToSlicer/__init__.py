"""RhinoToSlicer Rhino Python plug-in."""

from .Plugin import plug_in  # noqa: F401  - ensures plug-in loads on import

__all__ = ["__version__", "plug_in"]
__version__ = "0.2.0"
