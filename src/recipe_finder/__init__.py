"""Terminal tool that finds recipes from the ingredients and nutrition the user wants."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("recipe-finder")
except PackageNotFoundError:  # Running from a source tree that is not installed.
    __version__ = "0.0.0"
