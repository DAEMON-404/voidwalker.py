"""Host operating-system and CPU-architecture detection.

VoidWalker needs to know two things about the machine it runs on:

* the **operating system** — to pick the right package manager and binary flavour
  (``linux`` / ``darwin`` / ``windows``); and
* the **CPU architecture** — so that on ARM boxes (Apple Silicon, Raspberry Pi,
  AWS Graviton and other arm64/armv7 hardware) we install binaries that actually
  run, instead of blindly grabbing the ``amd64`` build.

The rest of the codebase talks about architectures using a small, normalised
vocabulary: ``amd64``, ``arm64``, ``armv7`` and ``386``.  Raw values reported by
``platform.machine()`` (``x86_64``, ``aarch64``, ``armv7l`` …) are mapped onto
that vocabulary by :func:`normalise_arch`.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass

# Canonical architecture tokens used throughout the catalog.
ARCH_AMD64 = "amd64"
ARCH_ARM64 = "arm64"
ARCH_ARMV7 = "armv7"
ARCH_386 = "386"

# Map the many spellings emitted by platform.machine()/uname -m onto our tokens.
_ARCH_ALIASES = {
    "x86_64": ARCH_AMD64,
    "x64": ARCH_AMD64,
    "amd64": ARCH_AMD64,
    "aarch64": ARCH_ARM64,
    "aarch64_be": ARCH_ARM64,
    "arm64": ARCH_ARM64,
    "armv8": ARCH_ARM64,
    "armv8l": ARCH_ARM64,
    "armv8b": ARCH_ARM64,
    "armv7l": ARCH_ARMV7,
    "armv7": ARCH_ARMV7,
    "armv6l": ARCH_ARMV7,
    "armhf": ARCH_ARMV7,
    "arm": ARCH_ARMV7,
    "i386": ARCH_386,
    "i486": ARCH_386,
    "i586": ARCH_386,
    "i686": ARCH_386,
    "x86": ARCH_386,
}

# Supported OS tokens.
OS_LINUX = "linux"
OS_DARWIN = "darwin"
OS_WINDOWS = "windows"


def normalise_arch(machine: str) -> str:
    """Map a raw ``platform.machine()`` value onto a canonical arch token.

    Unknown architectures are returned lower-cased and untouched so the caller
    can still log/skip cleanly instead of crashing.
    """
    return _ARCH_ALIASES.get(machine.strip().lower(), machine.strip().lower())


def detect_arch() -> str:
    """Return the canonical architecture token for the current machine."""
    return normalise_arch(platform.machine())


def detect_os() -> str:
    """Return the canonical OS token for the current machine."""
    if sys.platform.startswith("linux"):
        return OS_LINUX
    if sys.platform == "darwin":
        return OS_DARWIN
    if sys.platform.startswith(("win", "cygwin", "msys")):
        return OS_WINDOWS
    # Fall back to the raw platform string; callers degrade gracefully.
    return sys.platform


@dataclass(frozen=True)
class HostInfo:
    """Immutable description of the host we are running on."""

    os: str
    arch: str

    @classmethod
    def current(cls) -> "HostInfo":
        return cls(os=detect_os(), arch=detect_arch())

    # Convenience predicates kept for readability / backwards compatibility.
    @property
    def is_linux(self) -> bool:
        return self.os == OS_LINUX

    @property
    def is_macos(self) -> bool:
        return self.os == OS_DARWIN

    @property
    def is_windows(self) -> bool:
        return self.os == OS_WINDOWS

    @property
    def is_arm(self) -> bool:
        return self.arch in (ARCH_ARM64, ARCH_ARMV7)

    @property
    def deb_arch(self) -> str:
        """Debian package architecture name for this host (dpkg/apt naming)."""
        return {
            ARCH_AMD64: "amd64",
            ARCH_ARM64: "arm64",
            ARCH_ARMV7: "armhf",
            ARCH_386: "i386",
        }.get(self.arch, self.arch)

    def label(self) -> str:
        return f"{self.os}/{self.arch}"


def select_asset(assets: dict, host: HostInfo, *, fallback_amd64: bool = False):
    """Pick the asset list matching ``host`` from an ``(os, arch)``-keyed dict.

    ``assets`` maps ``(os, arch)`` tuples to a list of ``(filename, url)`` pairs.

    Resolution order:
      1. exact ``(host.os, host.arch)`` match;
      2. only if ``fallback_amd64`` is explicitly enabled (e.g. macOS/Rosetta),
         fall back to the host OS's amd64 build;
      3. otherwise ``None`` — the caller should skip with a clear message.

    The default is **no fallback**: for host-native binaries an amd64 build that
    cannot run on an ARM host is worse than a clean skip (the installer routes
    such tools to a from-source path like ``cargo``/``go install`` instead).
    """
    exact = assets.get((host.os, host.arch))
    if exact:
        return exact
    if fallback_amd64 and host.arch != ARCH_AMD64:
        fallback = assets.get((host.os, ARCH_AMD64))
        if fallback:
            return fallback
    return None
