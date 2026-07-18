"""VoidWalker — penetration-testing arsenal builder & workspace manager.

A modular Python package (formerly a single 4,000-line script) that provisions
an offensive workstation across Linux/macOS and x86_64/ARM hardware, scaffolds
an Obsidian engagement vault, and ships offline search helpers.
"""

from .version import __version__

__all__ = ["__version__", "VoidWalker"]


def __getattr__(name):
    # Lazy import so `import voidwalker` (and `--version`) stays cheap and avoids
    # pulling the full installer stack until the orchestrator is actually used.
    if name == "VoidWalker":
        from .core import VoidWalker
        return VoidWalker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
