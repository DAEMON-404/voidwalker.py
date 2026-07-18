#!/usr/bin/env python3
"""VoidWalker launcher.

The implementation now lives in the :mod:`voidwalker` package. This thin shim
keeps the historical ``python3 voidwalker.py [command]`` invocation working when
running straight from a checkout (no install needed). Once installed via
``pip install .`` the ``voidwalker`` console command does the same thing.
"""

import os
import sys

# Make the package importable when run as a loose script from the repo root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voidwalker.cli import main

if __name__ == "__main__":
    main()
