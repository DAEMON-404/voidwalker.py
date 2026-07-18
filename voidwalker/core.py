"""The VoidWalker orchestrator, composed from behaviour mixins.

The original 2,000-line ``VoidWalker`` class was split into focused mixins
(UI, downloads, installers, cross-platform binaries, vault, core orchestration).
This module re-assembles them into the single public class and owns the
constructor, where host OS/architecture detection now happens.
"""

from __future__ import annotations

import shutil
import signal
import sys
from pathlib import Path

from .hostinfo import HostInfo
from .ui import UIMixin
from .download import DownloadMixin
from .installers import InstallerMixin
from .xplat import CrossPlatformMixin
from .vault import VaultMixin
from .integrations.kali import KaliFixMixin
from .integrations.penv import PentestEnvMixin
from .integrations.bloodhound import BloodHoundMixin
from .integrations.proxy import ProxyMixin
from .integrations.recorder import RecorderMixin
from .integrations.rootsetup import RootSetupMixin
from ._core_methods import _CoreMethods


class VoidWalker(UIMixin, DownloadMixin, InstallerMixin,
                 CrossPlatformMixin, VaultMixin,
                 KaliFixMixin, PentestEnvMixin, BloodHoundMixin,
                 ProxyMixin, RecorderMixin, RootSetupMixin, _CoreMethods):
    def __init__(self):
        self.term_width = shutil.get_terminal_size().columns
        self.term_height = shutil.get_terminal_size().lines
        self.running = True
        self.base_path = Path.home() / "voidwalker"
        self.log_file = self.base_path / "voidwalker.log"
        self.stats = {"ok": 0, "fail": 0}
        # OS + CPU architecture detection drives binary/package selection so the
        # toolkit works on x86_64 *and* ARM (arm64/aarch64, armv7) hardware.
        self.host = HostInfo.current()
        self.platform = sys.platform  # retained for backwards compatibility
        self.is_macos = self.host.is_macos
        self.is_linux = self.host.is_linux
        # Make git non-interactive process-wide so neither our own clones nor
        # the ones run by spawned installer scripts prompt for a GitHub
        # username / password / email when they hit an unreachable repo.
        self.harden_git_environment()
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
