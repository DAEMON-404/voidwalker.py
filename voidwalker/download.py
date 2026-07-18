"""Download / extraction / subprocess helpers.

Auto-extracted from the original monolithic voidwalker.py; method bodies are
unchanged except where noted. Part of the VoidWalker package refactor.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import random
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from .version import __version__
from .theme import Colors, Symbols
from .hostinfo import HostInfo, select_asset
from .data.workspace import WORKSPACE_DIRS
from .data.catalog import TOOL_CATEGORIES
from .data.packages import (
    APT_TOOLS, BREW_TOOLS, BREW_CASKS, PIPX_TOOLS,
    GO_TOOLS, CARGO_TOOLS, GEM_TOOLS, UV_TOOLS,
)
from .data.binaries import CROSS_PLATFORM_TOOLS, SPECIAL_TOOLS
from .data.build_targets import BUILD_TARGETS
from .data.sources import SOURCES_AND_GUIDES


# --- Non-interactive git ----------------------------------------------------
# The installer clones many public GitHub repos unattended, in parallel. If one
# is private, renamed, or removed, git tries to authenticate — and on Windows,
# via Git Credential Manager, that pops a username / password / email prompt for
# *every* such repo, burying the user in dialogs (the reported symptom). These
# flags and env vars make every git invocation fail fast instead of prompting:
#   * GIT_TERMINAL_PROMPT=0            git's own terminal prompt off
#   * -c credential.helper=           disable any configured helper (e.g. GCM),
#                                     so it can't raise its own GUI/browser auth
#   * -c credential.interactive=false /
#     GCM_INTERACTIVE=Never           silence Git Credential Manager
#   * empty GIT_ASKPASS / SSH_ASKPASS +
#     -c core.askPass=                no GUI askpass helper gets launched
#   * GIT_SSH_COMMAND=... BatchMode   no SSH passphrase / host-key prompts
# A repo that needs auth is then simply counted as a failed download, which is
# the right outcome for an unattended arsenal fetch.
_GIT_NONINTERACTIVE_FLAGS = [
    "-c", "credential.helper=",
    "-c", "credential.interactive=false",
    "-c", "core.askPass=",
]

_GIT_NONINTERACTIVE_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GCM_INTERACTIVE": "Never",
    "GIT_ASKPASS": "",
    "SSH_ASKPASS": "",
}


class DownloadMixin:
    def download_file(self, url: str, dest: Path, timeout: int = 120, max_retries: int = 3) -> bool:
        if dest.exists() and dest.stat().st_size > 0:
            self.log(f"Skipped existing file: {dest}")
            return True

        for attempt in range(max_retries):
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    with open(dest, 'wb') as f:
                        f.write(resp.read())
                if dest.suffix in ['', '.sh', '.py']:
                    dest.chmod(0o755)
                self.log(f"Successfully downloaded {url} to {dest}")
                return True
            except Exception as e:
                self.log(f"Download failed for {url} (Attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return False

    def download_and_extract_zip(self, url: str, dest: Path, timeout: int = 120, max_retries: int = 3) -> bool:
        if dest.exists() and any(dest.iterdir()):
            self.log(f"Skipped existing directory: {dest}")
            return True

        for attempt in range(max_retries):
            try:
                dest.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        tmp.write(resp.read())
                    tmp_path = tmp.name
                
                with zipfile.ZipFile(tmp_path, 'r') as zf:
                    zf.extractall(dest)
                os.unlink(tmp_path)
                self.log(f"Successfully downloaded and extracted {url} to {dest}")
                return True
            except Exception as e:
                self.log(f"ZIP Download failed for {url} (Attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return False

    @staticmethod
    def harden_git_environment() -> None:
        """Make git non-interactive for this process and every child it spawns.

        Called once at startup so that git clones run by the spawned installer
        shell scripts (pimpmykali, pentest-env) inherit the same no-prompt
        behaviour as our own :meth:`git_clone`, rather than only the git
        commands we launch directly.
        """
        os.environ.update(_GIT_NONINTERACTIVE_ENV)
        os.environ.setdefault("GIT_SSH_COMMAND", "ssh -oBatchMode=yes")

    def run_git(self, args: List[str], timeout: int = 120):
        """Run a git subcommand fully non-interactively.

        Prepends the credential-suppressing ``-c`` flags, forces a
        non-interactive environment, and closes stdin so git can never block
        (or, on Windows, pop a Credential Manager dialog) waiting for input.
        Returns the :class:`subprocess.CompletedProcess`.
        """
        env = os.environ.copy()
        env.update(_GIT_NONINTERACTIVE_ENV)
        env.setdefault("GIT_SSH_COMMAND", "ssh -oBatchMode=yes")
        return subprocess.run(
            ["git", *_GIT_NONINTERACTIVE_FLAGS, *args],
            capture_output=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env=env,
        )

    def git_clone(self, url: str, dest: Path, timeout: int = 120, max_retries: int = 3) -> bool:
        if (dest / ".git").exists():
            try:
                self.run_git(["-C", str(dest), "pull", "--ff-only"], timeout=timeout)
                self.log(f"Updated existing repo: {dest}")
                return True
            except Exception as e:
                self.log(f"Failed to pull existing repo {dest}: {str(e)}")
                return False
        elif dest.exists():
            self.log(f"Skipped existing directory without .git: {dest}")
            return True

        for attempt in range(max_retries):
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                result = self.run_git(["clone", "--depth=1", url, str(dest)], timeout=timeout)
                if result.returncode == 0:
                    self.log(f"Successfully cloned {url} to {dest}")
                    return True
                else:
                    self.log(f"Clone failed for {url} (Attempt {attempt+1}/{max_retries}): {result.stderr.decode(errors='ignore')}")
            except Exception as e:
                self.log(f"Clone exception for {url} (Attempt {attempt+1}/{max_retries}): {str(e)}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        return False

    def run_cmd(self, cmd: List[str], timeout: int = 300) -> bool:
        try:
            # stdin=DEVNULL: this installer runs unattended, so a child must
            # never block waiting for input. Without it, an apt/debconf postinst
            # prompt (e.g. pulled in by `wifite`) reads the inherited terminal
            # stdin while its output is captured/hidden, wedging the whole run.
            result = subprocess.run(
                cmd, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL
            )
            if result.returncode != 0:
                self.log(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr.decode(errors='ignore')}")
            return result.returncode == 0
        except Exception as e:
            self.log(f"Command exception: {' '.join(cmd)}\nError: {str(e)}")
            return False

    def _download_and_extract_tar_gz(self, url: str, dest_dir: Path, tool_name: str) -> bool:
        """Download a .tar.gz archive and extract all files into dest_dir."""
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    tmp.write(resp.read())
                tmp_path = Path(tmp.name)

            with tarfile.open(tmp_path, 'r:gz') as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        member.name = Path(member.name).name  # flatten path
                        tar.extract(member, dest_dir)
                        extracted = dest_dir / member.name
                        if extracted.exists():
                            extracted.chmod(0o755)

            tmp_path.unlink(missing_ok=True)
            return True
        except Exception:
            return False

    def _download_and_decompress_gz(self, url: str, dest_file: Path) -> bool:
        """Download a .gz file and decompress it to dest_file."""
        try:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(suffix='.gz', delete=False) as tmp:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    tmp.write(resp.read())
                tmp_path = Path(tmp.name)

            with gzip.open(tmp_path, 'rb') as f_in:
                with open(dest_file, 'wb') as f_out:
                    f_out.write(f_in.read())

            tmp_path.unlink(missing_ok=True)
            if dest_file.exists():
                dest_file.chmod(0o755)
            return dest_file.exists()
        except Exception:
            return False

