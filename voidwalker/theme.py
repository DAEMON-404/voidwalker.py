"""Centralised colour palette and glyphs for the VoidWalker TUI.

The whole UI reads colours from the :class:`Colors` class and glyphs from
:class:`Symbols`.  Historically the palette was hard-coded to the light
*Rosé Pine Dawn* scheme, which clashed with VoidWalker's neon "cyberpunk"
branding.  Colours now live in named themes (:data:`THEMES`) and can be swapped
at runtime via :func:`apply_theme` (CLI ``--theme`` / ``VOIDWALKER_THEME`` env).

``Colors`` keeps the original attribute *names* so every existing call site
(``Colors.NEON_CYAN`` …) continues to work — only the values change with the
active theme.
"""

from __future__ import annotations

import os


def _fg(r: int, g: int, b: int) -> str:
    """24-bit truecolor foreground escape."""
    return f"\033[38;2;{r};{g};{b}m"


# Each theme maps the canonical colour roles to RGB triples.
THEMES = {
    # Default: neon on dark — true to the VOIDWALKER cyberpunk branding.
    "voidwalker": {
        "NEON_CYAN": (0, 255, 249),
        "NEON_MAGENTA": (255, 45, 149),
        "NEON_GREEN": (0, 255, 159),
        "ELECTRIC_BLUE": (64, 160, 255),
        "DEEP_PURPLE": (138, 43, 226),
        "BRIGHT_RED": (255, 64, 96),
        "ORANGE": (255, 176, 0),
        "YELLOW": (255, 209, 102),
        "WHITE": (233, 236, 245),
        "GRAY": (122, 130, 155),
        "DARK_CYAN": (0, 180, 176),
        "ROSE": (255, 120, 170),
        "SUBTLE": (90, 96, 120),
        "BASE": (224, 226, 235),
        "SURFACE": (200, 205, 220),
        "OVERLAY": (150, 156, 180),
    },
    # Alternate: the original light Rosé Pine Dawn palette.
    "rosepine": {
        "NEON_CYAN": (86, 148, 159),
        "NEON_MAGENTA": (144, 122, 169),
        "NEON_GREEN": (40, 105, 131),
        "ELECTRIC_BLUE": (86, 148, 159),
        "DEEP_PURPLE": (144, 122, 169),
        "BRIGHT_RED": (180, 99, 122),
        "ORANGE": (234, 157, 52),
        "YELLOW": (234, 157, 52),
        "WHITE": (87, 82, 121),
        "GRAY": (152, 147, 165),
        "DARK_CYAN": (40, 105, 131),
        "ROSE": (215, 130, 126),
        "SUBTLE": (121, 117, 147),
        "BASE": (250, 244, 237),
        "SURFACE": (255, 250, 243),
        "OVERLAY": (242, 233, 225),
    },
    # Alternate: matrix-style mono-green.
    "matrix": {
        "NEON_CYAN": (0, 255, 70),
        "NEON_MAGENTA": (0, 200, 55),
        "NEON_GREEN": (0, 255, 70),
        "ELECTRIC_BLUE": (0, 180, 50),
        "DEEP_PURPLE": (0, 220, 60),
        "BRIGHT_RED": (255, 80, 80),
        "ORANGE": (120, 255, 120),
        "YELLOW": (160, 255, 120),
        "WHITE": (200, 255, 200),
        "GRAY": (70, 130, 80),
        "DARK_CYAN": (0, 160, 45),
        "ROSE": (90, 255, 120),
        "SUBTLE": (40, 90, 50),
        "BASE": (200, 255, 200),
        "SURFACE": (160, 230, 160),
        "OVERLAY": (90, 160, 100),
    },
}

DEFAULT_THEME = "voidwalker"


class Colors:
    """Active palette. Attribute values are (re)assigned by :func:`apply_theme`."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    # Colour-role attributes below are populated by apply_theme() at import time.


def apply_theme(name: str) -> str:
    """Apply the named theme to :class:`Colors`. Returns the name actually used."""
    palette = THEMES.get(name) or THEMES[DEFAULT_THEME]
    for role, (r, g, b) in palette.items():
        setattr(Colors, role, _fg(r, g, b))
    apply_theme.current = name if name in THEMES else DEFAULT_THEME
    return apply_theme.current


def list_themes() -> list[str]:
    return sorted(THEMES)


# Apply the env-selected (or default) theme as soon as the module is imported,
# so every Colors.* attribute exists before any UI code runs.
apply_theme(os.environ.get("VOIDWALKER_THEME", DEFAULT_THEME))


class Symbols:
    BLOCK_FULL = "█"
    BLOCK_LIGHT = "░"
    BLOCK_MED = "▒"
    BLOCK_DARK = "▓"
    ARROW_RIGHT = "►"
    DIAMOND = "◆"
    CIRCLE = "●"
    STAR = "★"
    CHECK = "✓"
    CROSS = "✗"
    LIGHTNING = "⚡"
    GEAR = "⚙"
    SHIELD = "🛡"
    ROCKET = "🚀"
    BOX_TL = "╔"
    BOX_TR = "╗"
    BOX_BL = "╚"
    BOX_BR = "╝"
    BOX_H = "═"
    BOX_V = "║"
    CYBER_CHARS = "ヲアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン"
