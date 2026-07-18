"""Package-manager and binary installers.

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


class InstallerMixin:
    def install_system_tools(self):
        """Route to the correct OS-specific package installer."""
        if self.is_macos:
            self.install_brew_tools()
        else:
            self.install_apt_tools()

    def install_metasploit(self):
        """Install the Metasploit Framework (msfconsole) as a standalone action.

        Cross-platform: on macOS this pulls the official Homebrew cask (the signed
        omnibus .pkg); on Linux it runs Rapid7's omnibus nightly installer — the
        vendor-recommended path for every distro, which wires up the apt/yum repo
        so future updates are a plain `msfupdate` / `apt upgrade`.

        Metasploit also ships inside the full arsenal via the `metasploit-framework`
        apt package, but that only fires on Debian/Kali; this menu entry is the
        quick, no-frills way to get just msfconsole — and the only path that
        covers macOS, where it is absent from the brew formulae list.
        """
        self.clear_screen()
        self.show_ascii_banner()

        print()
        self.print_centered(f"{Colors.NEON_MAGENTA}{Symbols.LIGHTNING} INSTALL METASPLOIT FRAMEWORK {Symbols.LIGHTNING}{Colors.RESET}")
        self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
        print()

        # Already on PATH? Report the version and bail — re-running the vendor
        # installer would just churn apt/brew for no gain.
        existing = shutil.which("msfconsole")
        if existing:
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} msfconsole already installed{Colors.RESET} "
                  f"{Colors.GRAY}({existing}){Colors.RESET}")
            self._print_msf_version()
            print()
            input(f"{Colors.GRAY}Press Enter to continue...{Colors.RESET}")
            return

        ok = self._install_metasploit_macos() if self.is_macos else self._install_metasploit_linux()

        print()
        if ok and shutil.which("msfconsole"):
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} Metasploit Framework installed{Colors.RESET}")
            self._print_msf_version()
            self.stats["ok"] += 1
            print()
            print(f"  {Colors.ELECTRIC_BLUE}Next steps:{Colors.RESET}")
            print(f"  {Colors.WHITE}  msfdb init  {Colors.GRAY}# set up the PostgreSQL backend (optional){Colors.RESET}")
            print(f"  {Colors.WHITE}  msfconsole  {Colors.GRAY}# launch the console{Colors.RESET}")
        else:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} Metasploit installation failed{Colors.RESET}")
            print(f"  {Colors.GRAY}See {self.log_file} for details.{Colors.RESET}")
            self.stats["fail"] += 1

        print()
        input(f"{Colors.GRAY}Press Enter to continue...{Colors.RESET}")

    def _print_msf_version(self):
        """Print the first line of `msfconsole --version`, if it answers."""
        try:
            result = subprocess.run(
                ["msfconsole", "--version"],
                capture_output=True, timeout=60, stdin=subprocess.DEVNULL,
            )
            lines = result.stdout.decode(errors="ignore").strip().splitlines()
            if lines:
                print(f"  {Colors.GRAY}{lines[0].strip()}{Colors.RESET}")
        except Exception:
            pass

    def _install_metasploit_macos(self) -> bool:
        """macOS: install the vendor Homebrew cask (runs the signed .pkg)."""
        if not shutil.which("brew"):
            print(f"  {Colors.YELLOW}Homebrew not found — installing...{Colors.RESET}")
            self.run_cmd(
                ["bash", "-c",
                 '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'],
                timeout=1800,
            )
        else:
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} Homebrew detected{Colors.RESET}")

        done_event = threading.Event()
        spinner = threading.Thread(
            target=self.spinner_animation,
            args=("Installing metasploit cask (downloads ~1GB)...", done_event),
        )
        spinner.start()
        ok = self.run_cmd(["brew", "install", "--cask", "metasploit"], timeout=1800)
        done_event.set()
        spinner.join()
        return ok

    def _install_metasploit_linux(self) -> bool:
        """Linux: run Rapid7's omnibus nightly installer (apt/yum, any distro)."""
        installer_url = ("https://raw.githubusercontent.com/rapid7/metasploit-omnibus/"
                         "master/config/templates/metasploit-framework-wrappers/msfupdate.erb")
        installer = Path("/tmp/msfinstall")

        print(f"  {Colors.YELLOW}Fetching Rapid7 omnibus installer...{Colors.RESET}")
        # Force a fresh copy: download_file skips existing files, but the vendor
        # updates this wrapper, so a stale /tmp/msfinstall could be days old.
        try:
            installer.unlink(missing_ok=True)
        except Exception:
            pass
        if not self.download_file(installer_url, installer):
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} Could not download the installer{Colors.RESET}")
            return False
        installer.chmod(0o755)
        print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} Installer downloaded{Colors.RESET}")

        # `sudo env DEBIAN_FRONTEND=noninteractive` mirrors the apt path: the
        # omnibus postinst pulls packages via apt, and without this guard a
        # debconf prompt would block this capture_output/stdin=DEVNULL run.
        done_event = threading.Event()
        spinner = threading.Thread(
            target=self.spinner_animation,
            args=("Installing Metasploit (this can take several minutes)...", done_event),
        )
        spinner.start()
        ok = self.run_cmd(
            ["sudo", "env",
             "DEBIAN_FRONTEND=noninteractive",
             "DEBCONF_NONINTERACTIVE_SEEN=true",
             str(installer)],
            timeout=1800,
        )
        done_event.set()
        spinner.join()
        return ok

    # AI coding CLIs are npm globals (arch-independent JS launchers; codex pulls
    # its per-arch Rust binary via npm optional-deps, so both resolve on arm64).
    _AI_CLIS = [
        ("Claude Code", "claude", "@anthropic-ai/claude-code"),
        ("Codex CLI", "codex", "@openai/codex"),
    ]

    def install_ai_clis(self):
        """Install AI coding CLIs (Claude Code + OpenAI Codex) as a menu section.

        Both ship as npm global packages, so they install identically on x86_64
        and arm64. Claude Code additionally has an official native installer
        (no sudo, drops a binary in ~/.local/bin) which is tried first.
        """
        self.clear_screen()
        self.show_ascii_banner()

        print()
        self.print_centered(f"{Colors.NEON_MAGENTA}{Symbols.STAR} INSTALL AI CODE AGENTS {Symbols.STAR}{Colors.RESET}")
        self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
        print()

        if not self._ensure_node():
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} Node.js/npm unavailable — cannot install the AI CLIs{Colors.RESET}")
            print()
            input(f"{Colors.GRAY}Press Enter to continue...{Colors.RESET}")
            return

        claude_ok = self._install_claude_code()
        codex_ok = self._npm_global_install("@openai/codex")

        print()
        for (label, binname, _pkg), ok in zip(self._AI_CLIS, (claude_ok, codex_ok)):
            found = self._which_cli(binname)
            if ok and found:
                print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} {label} installed{Colors.RESET} {Colors.GRAY}({found}){Colors.RESET}")
                self._print_cli_version(found)
                self.stats["ok"] += 1
            else:
                print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} {label} installation failed{Colors.RESET}")
                self.stats["fail"] += 1

        print()
        print(f"  {Colors.GRAY}If a CLI isn't found, restart your shell (adds ~/.local/bin + npm global bin to PATH).{Colors.RESET}")
        print()
        input(f"{Colors.GRAY}Press Enter to continue...{Colors.RESET}")

    def _which_cli(self, binname: str):
        """Locate a CLI on PATH, or in ~/.local/bin (where the native installers land)."""
        found = shutil.which(binname)
        if found:
            return found
        local = Path.home() / ".local" / "bin" / binname
        return str(local) if local.exists() else None

    def _print_cli_version(self, binpath: str):
        try:
            result = subprocess.run(
                [binpath, "--version"],
                capture_output=True, timeout=60, stdin=subprocess.DEVNULL,
            )
            lines = result.stdout.decode(errors="ignore").strip().splitlines()
            if lines:
                print(f"  {Colors.GRAY}{lines[0].strip()}{Colors.RESET}")
        except Exception:
            pass

    def _ensure_node(self) -> bool:
        """Make sure node/npm are present, installing them if missing."""
        if shutil.which("npm"):
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} Node.js/npm detected{Colors.RESET}")
            return True
        print(f"  {Colors.YELLOW}Node.js/npm not found — installing...{Colors.RESET}")
        if self.is_macos:
            if not shutil.which("brew"):
                self.run_cmd(
                    ["bash", "-c",
                     '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'],
                    timeout=1800,
                )
            self.run_cmd(["brew", "install", "node"], timeout=1800)
        else:
            self.run_cmd(
                ["sudo", "env", "DEBIAN_FRONTEND=noninteractive",
                 "apt-get", "install", "-y", "nodejs", "npm"],
                timeout=1800,
            )
        return shutil.which("npm") is not None

    def _npm_global_install(self, pkg: str) -> bool:
        """`npm install -g pkg`, adding sudo on Linux when not already root."""
        cmd = ["npm", "install", "-g", pkg]
        if self.is_linux and hasattr(os, "geteuid") and os.geteuid() != 0:
            cmd = ["sudo"] + cmd
        done_event = threading.Event()
        spinner = threading.Thread(
            target=self.spinner_animation,
            args=(f"npm install -g {pkg}...", done_event),
        )
        spinner.start()
        ok = self.run_cmd(cmd, timeout=600)
        done_event.set()
        spinner.join()
        return ok

    def _install_claude_code(self) -> bool:
        """Claude Code: official native installer first (no sudo, arch-aware), npm fallback."""
        done_event = threading.Event()
        spinner = threading.Thread(
            target=self.spinner_animation,
            args=("Installing Claude Code (native installer)...", done_event),
        )
        spinner.start()
        native_ok = self.run_cmd(
            ["bash", "-c", "curl -fsSL https://claude.ai/install.sh | bash"],
            timeout=600,
        )
        done_event.set()
        spinner.join()
        if native_ok and self._which_cli("claude"):
            return True
        # Fallback to the npm global package.
        return self._npm_global_install("@anthropic-ai/claude-code")

    def install_brew_tools(self):
        """Install system packages on macOS via Homebrew."""
        self.clear_screen()
        self.show_ascii_banner()

        print()
        self.print_centered(f"{Colors.NEON_MAGENTA}{Symbols.ROCKET} INSTALLING SYSTEM PACKAGES (macOS/Homebrew) {Symbols.ROCKET}{Colors.RESET}")
        self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
        print()

        # Ensure Homebrew is installed
        brew_check = subprocess.run(["which", "brew"], capture_output=True)
        if brew_check.returncode != 0:
            print(f"  {Colors.YELLOW}Homebrew not found — installing...{Colors.RESET}")
            self.run_cmd(["bash", "-c",
                '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'])
        else:
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} Homebrew detected{Colors.RESET}")

        # Update Homebrew
        done_event = threading.Event()
        spinner_thread = threading.Thread(
            target=self.spinner_animation,
            args=("Updating Homebrew...", done_event)
        )
        spinner_thread.start()
        self.run_cmd(["brew", "update"])
        done_event.set()
        spinner_thread.join()
        print(f"  {Colors.NEON_GREEN}{Symbols.CHECK}{Colors.RESET} {Colors.WHITE}Homebrew updated{Colors.RESET}")
        print()

        # Install brew formulae
        brew_success, brew_fail = 0, 0
        total_brew = len(BREW_TOOLS)

        for i, tool in enumerate(BREW_TOOLS, 1):
            self.show_live_status("Brew Formulae", i, total_brew, tool, "downloading")
            if self.run_cmd(["brew", "install", tool]):
                brew_success += 1
                self.stats["ok"] += 1
            else:
                brew_fail += 1
                self.stats["fail"] += 1

        self.complete_status_line("Brew Formulae", brew_success, brew_fail)
        print()

        # Install brew casks
        cask_success, cask_fail = 0, 0
        total_cask = len(BREW_CASKS)

        for i, cask in enumerate(BREW_CASKS, 1):
            self.show_live_status("Brew Casks", i, total_cask, cask, "downloading")
            if self.run_cmd(["brew", "install", "--cask", cask]):
                cask_success += 1
                self.stats["ok"] += 1
            else:
                cask_fail += 1
                self.stats["fail"] += 1

        self.complete_status_line("Brew Casks", cask_success, cask_fail)
        print()

        # Ensure pipx is available
        self.run_cmd(["pipx", "ensurepath"])

        # PIPX tools
        pipx_success, pipx_fail = 0, 0
        total_pipx = len(PIPX_TOOLS)

        for i, tool in enumerate(PIPX_TOOLS, 1):
            self.show_live_status("PIPX Tools", i, total_pipx, tool, "downloading")
            if self.run_cmd(["pipx", "install", tool]):
                pipx_success += 1
                self.stats["ok"] += 1
            else:
                pipx_fail += 1

        self.complete_status_line("PIPX Tools", pipx_success, pipx_fail)
        print()

        # UV tools
        self.install_uv_tools()

        # Go tools (brew installs go already)
        go_success, go_fail = 0, 0
        total_go = len(GO_TOOLS)
        os.environ["GOPATH"] = str(Path.home() / "go")
        os.environ["PATH"] = os.environ.get("PATH", "") + ":" + str(Path.home() / "go" / "bin")

        for i, (name, cmd) in enumerate(GO_TOOLS, 1):
            self.show_live_status("Go Tools", i, total_go, name, "downloading")
            if cmd.startswith("go install"):
                if self.run_cmd(cmd.split()):
                    go_success += 1
                    self.stats["ok"] += 1
                else:
                    go_fail += 1
                    self.stats["fail"] += 1
            # Skip .deb files on macOS
            elif cmd.endswith(".deb"):
                go_fail += 1
                self.stats["fail"] += 1

        self.complete_status_line("Go Tools", go_success, go_fail)
        print()

        self._install_cargo_tools(sudo=False)

        # Ruby Gems
        gem_success, gem_fail = 0, 0
        total_gem = len(GEM_TOOLS)
        if total_gem > 0:
            for i, tool in enumerate(GEM_TOOLS, 1):
                self.show_live_status("Ruby Gems", i, total_gem, tool, "downloading")
                if self.run_cmd(["gem", "install", tool]):
                    gem_success += 1
                    self.stats["ok"] += 1
                else:
                    gem_fail += 1
                    self.stats["fail"] += 1
            self.complete_status_line("Ruby Gems", gem_success, gem_fail)
            print()

        # Cross-Platform Tools (all three platforms)
        self.install_cross_platform_tools()

        # Shell aliases (zsh on macOS)
        self.create_shell_aliases()

        self.show_summary()

    def install_apt_tools(self):
        self.clear_screen()
        self.show_ascii_banner()

        print()
        self.print_centered(f"{Colors.NEON_MAGENTA}{Symbols.ROCKET} INSTALLING SYSTEM PACKAGES {Symbols.ROCKET}{Colors.RESET}")
        self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
        print()

        # Force debconf to take package defaults instead of opening interactive
        # dialogs. `apt-get -y` only auto-answers apt's own prompt, not debconf
        # (e.g. macchanger/wireshark postinst), which would otherwise hang an
        # unattended run — the 'stuck on wifite' symptom.
        os.environ["DEBIAN_FRONTEND"] = "noninteractive"
        os.environ["DEBCONF_NONINTERACTIVE_SEEN"] = "true"
        
        done_event = threading.Event()
        spinner_thread = threading.Thread(
            target=self.spinner_animation,
            args=("Updating package lists...", done_event)
        )
        spinner_thread.start()
        self.run_cmd(["sudo", "apt-get", "update"])
        done_event.set()
        spinner_thread.join()
        print(f"  {Colors.NEON_GREEN}{Symbols.CHECK}{Colors.RESET} {Colors.WHITE}Package lists updated{Colors.RESET}")
        print()
        
        apt_success, apt_fail = 0, 0
        total_apt = len(APT_TOOLS)
        
        apt_opts = [
            "-y",
            "-o", "Dpkg::Options::=--force-confdef",
            "-o", "Dpkg::Options::=--force-confold",
        ]
        for i, tool in enumerate(APT_TOOLS, 1):
            self.show_live_status("APT Packages", i, total_apt, tool, "downloading")
            # `sudo env VAR=..` guarantees the var reaches apt regardless of the
            # sudoers env policy (plain `sudo VAR=..` needs SETENV; `-E` can be
            # stripped). This is what actually stops debconf from prompting.
            if self.run_cmd(["sudo", "env",
                             "DEBIAN_FRONTEND=noninteractive",
                             "DEBCONF_NONINTERACTIVE_SEEN=true",
                             "apt-get", "install", *apt_opts, tool]):
                apt_success += 1
                self.stats["ok"] += 1
            else:
                apt_fail += 1
                self.stats["fail"] += 1
        
        self.complete_status_line("APT Packages", apt_success, apt_fail)
        print()
        
        self.run_cmd(["pipx", "ensurepath"])
        
        pipx_success, pipx_fail = 0, 0
        total_pipx = len(PIPX_TOOLS)
        
        for i, tool in enumerate(PIPX_TOOLS, 1):
            self.show_live_status("PIPX Tools", i, total_pipx, tool, "downloading")
            if self.run_cmd(["pipx", "install", tool]):
                pipx_success += 1
                self.stats["ok"] += 1
            else:
                pipx_fail += 1
        
        self.complete_status_line("PIPX Tools", pipx_success, pipx_fail)
        print()

        # Install UV and UV-managed Python tools
        self.install_uv_tools()
        
        go_success, go_fail = 0, 0
        total_go = len(GO_TOOLS)
        
        os.environ["GOPATH"] = str(Path.home() / "go")
        os.environ["PATH"] = os.environ.get("PATH", "") + ":" + str(Path.home() / "go" / "bin")
        
        for i, (name, cmd) in enumerate(GO_TOOLS, 1):
            self.show_live_status("Go Tools", i, total_go, name, "downloading")
            if cmd.startswith("go install"):
                if self.run_cmd(cmd.split()):
                    go_success += 1
                    self.stats["ok"] += 1
                else:
                    go_fail += 1
                    self.stats["fail"] += 1
            elif cmd.endswith(".deb"):
                # Select the .deb matching this host's architecture; if upstream
                # ships none for it (e.g. armhf), skip and rely on cargo/go below.
                deb_arch = self.host.deb_arch
                deb_url = cmd.replace("_amd64.deb", f"_{deb_arch}.deb") if deb_arch != "amd64" else cmd
                deb_path = Path("/tmp") / f"{name}_{deb_arch}.deb"
                if deb_arch in ("amd64", "arm64") and self.download_file(deb_url, deb_path):
                    self.run_cmd(["sudo", "dpkg", "-i", str(deb_path)])
                    go_success += 1
                    self.stats["ok"] += 1
                else:
                    self.log(f"{name}: no .deb for {deb_arch}; will try cargo instead")
                    go_fail += 1
                    self.stats["fail"] += 1

        self.complete_status_line("Go Tools", go_success, go_fail)
        print()

        self._install_cargo_tools(sudo=False)

        # Install Ruby Gems
        gem_success, gem_fail = 0, 0
        total_gem = len(GEM_TOOLS)

        if total_gem > 0:
            for i, tool in enumerate(GEM_TOOLS, 1):
                self.show_live_status("Ruby Gems", i, total_gem, tool, "downloading")
                if self.run_cmd(["sudo", "gem", "install", tool]):
                    gem_success += 1
                    self.stats["ok"] += 1
                else:
                    gem_fail += 1
                    self.stats["fail"] += 1

            self.complete_status_line("Ruby Gems", gem_success, gem_fail)
            print()

        # Install Special Tools (kerbrute)
        special_success, special_fail = 0, 0
        total_special = len(SPECIAL_TOOLS)

        if total_special > 0:
            for i, (name, config) in enumerate(SPECIAL_TOOLS.items(), 1):
                self.show_live_status("Special Tools", i, total_special, name, "downloading")
                if self.install_special_tool(name, config):
                    special_success += 1
                    self.stats["ok"] += 1
                else:
                    special_fail += 1
                    self.stats["fail"] += 1

            self.complete_status_line("Special Tools", special_success, special_fail)
            print()

        # Install Cross-Platform Tools (chisel, ligolo-ng, fscan — both Windows & Linux)
        self.install_cross_platform_tools()

        # Extract rockyou.txt if it exists
        self.extract_rockyou()

        # Switch bash → zsh (Debian defaults to bash) before writing aliases so
        # they land in ~/.zshrc, matching the pentest-env zsh config.
        self.ensure_zsh_default_shell()

        # Create shell aliases
        self.create_shell_aliases()

    def _install_cargo_tools(self, sudo: bool = False):
        """Install Rust/Cargo tools from source (architecture-independent).

        Compiling from crates.io works on x86_64 and ARM alike, which makes this
        the portable fallback for tools whose prebuilt binaries are x86-only.
        """
        total_cargo = len(CARGO_TOOLS)
        if total_cargo == 0 or not shutil.which("cargo"):
            return
        cargo_success, cargo_fail = 0, 0
        for i, tool in enumerate(CARGO_TOOLS, 1):
            self.show_live_status("Cargo Tools", i, total_cargo, tool, "downloading")
            if self.run_cmd(["cargo", "install", tool], timeout=900):
                cargo_success += 1
                self.stats["ok"] += 1
            else:
                cargo_fail += 1
                self.stats["fail"] += 1
        self.complete_status_line("Cargo Tools", cargo_success, cargo_fail)
        print()

        self.show_summary()

    def install_uv_tools(self):
        """Install UV package manager and UV-managed Python security tools."""
        print(f"  {Colors.YELLOW}Installing UV package manager...{Colors.RESET}")

        # Install UV via official installer
        uv_installed = self.run_cmd(
            ["bash", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"]
        )
        if uv_installed:
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} UV installed{Colors.RESET}")
        else:
            # Fallback: try pipx
            uv_installed = self.run_cmd(["pipx", "install", "uv"])
            if uv_installed:
                print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} UV installed via pipx{Colors.RESET}")
            else:
                print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} UV installation failed — skipping UV tools{Colors.RESET}")
                return

        # Ensure UV is on PATH
        uv_bin = Path.home() / ".local" / "bin"
        if str(uv_bin) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = str(uv_bin) + ":" + os.environ.get("PATH", "")

        uv_success, uv_fail = 0, 0
        total_uv = len(UV_TOOLS)

        for i, tool in enumerate(UV_TOOLS, 1):
            self.show_live_status("UV Tools", i, total_uv, tool, "downloading")
            if self.run_cmd(["uv", "tool", "install", tool]):
                uv_success += 1
                self.stats["ok"] += 1
            else:
                uv_fail += 1
                self.stats["fail"] += 1

        self.complete_status_line("UV Tools", uv_success, uv_fail)
        print()

    def extract_rockyou(self):
        """Extract rockyou.txt wordlist if it's compressed."""
        rockyou_gz = Path("/usr/share/wordlists/rockyou.txt.gz")
        rockyou_txt = Path("/usr/share/wordlists/rockyou.txt")

        if rockyou_gz.exists() and not rockyou_txt.exists():
            try:
                print(f"  {Colors.YELLOW}Extracting rockyou.txt...{Colors.RESET}")
                subprocess.run(["gunzip", str(rockyou_gz)], check=False)
                if rockyou_txt.exists():
                    print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} rockyou.txt extracted{Colors.RESET}")
                else:
                    print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} Failed to extract rockyou.txt{Colors.RESET}")
            except Exception:
                print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} Error extracting rockyou.txt{Colors.RESET}")
        elif rockyou_txt.exists():
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} rockyou.txt already available{Colors.RESET}")

    def build_dotnet_tool(self, name: str, config: Dict) -> bool:
        """Build a single C# tool from source using dotnet build.

        Args:
            name: Tool name (e.g. "Rubeus")
            config: Dict with keys: repo, framework, type (sln|csproj), description
        Returns:
            True if build succeeded, False otherwise
        """
        try:
            src_dir = self.base_path / "tools" / "build-src" / name
            out_dir = self.base_path / "tools" / "windows" / "compiled" / name
            out_dir.mkdir(parents=True, exist_ok=True)

            # Clone or update repo
            if src_dir.exists():
                # run_git (not run_cmd) so a private/moved repo fails fast
                # instead of triggering an interactive credential prompt.
                self.run_git(["-C", str(src_dir), "pull", "--ff-only"])
            else:
                if not self.git_clone(config["repo"], src_dir):
                    return False

            # Find the build file (.sln or .csproj)
            build_ext = ".sln" if config["type"] == "sln" else ".csproj"
            build_file = None

            # Search root first, then one level deep
            for f in src_dir.glob(f"*{build_ext}"):
                build_file = f
                break
            if not build_file:
                for f in src_dir.glob(f"*/*{build_ext}"):
                    build_file = f
                    break

            if not build_file:
                return False

            # Restore NuGet packages
            self.run_cmd(["dotnet", "restore", str(build_file)])

            # Build
            build_result = self.run_cmd([
                "dotnet", "build", str(build_file),
                "-c", "Release",
                "--no-restore",
            ])

            if not build_result:
                # Fallback: try without --no-restore
                build_result = self.run_cmd([
                    "dotnet", "build", str(build_file),
                    "-c", "Release",
                ])

            if not build_result:
                return False

            # Collect compiled binaries
            compiled_count = 0
            for exe in src_dir.rglob("bin/Release/**/*.exe"):
                dest = out_dir / exe.name
                shutil.copy2(str(exe), str(dest))
                compiled_count += 1
            for dll in src_dir.rglob("bin/Release/**/*.dll"):
                # Only copy DLLs that match the tool name (not all dependencies)
                if name.lower() in dll.name.lower():
                    dest = out_dir / dll.name
                    shutil.copy2(str(dll), str(dest))
                    compiled_count += 1

            return compiled_count > 0

        except Exception:
            return False

    def build_all_tools(self):
        """Clone and build all C# tools from BUILD_TARGETS."""
        self.clear_screen()
        self.show_ascii_banner()

        print()
        self.print_centered(f"{Colors.NEON_MAGENTA}{Symbols.GEAR} BUILD C# TOOLS FROM SOURCE {Symbols.GEAR}{Colors.RESET}")
        self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
        print()

        # Check for dotnet SDK
        dotnet_available = self.run_cmd(["dotnet", "--version"])
        if not dotnet_available:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} .NET SDK not found!{Colors.RESET}")
            print()
            print(f"  {Colors.YELLOW}Install the .NET SDK first:{Colors.RESET}")
            if self.is_macos:
                print(f"  {Colors.WHITE}  brew install dotnet-sdk{Colors.RESET}")
            else:
                print(f"  {Colors.WHITE}  sudo apt-get install -y dotnet-sdk-8.0{Colors.RESET}")
                print(f"  {Colors.WHITE}  — or —{Colors.RESET}")
                print(f"  {Colors.WHITE}  wget https://dot.net/v1/dotnet-install.sh && bash dotnet-install.sh{Colors.RESET}")
            print()
            print(f"  {Colors.GRAY}See BUILD_GUIDE.md for detailed instructions.{Colors.RESET}")
            print()
            input(f"{Colors.GRAY}Press Enter to continue...{Colors.RESET}")
            return

        print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} .NET SDK detected{Colors.RESET}")
        print()

        # Create directories
        src_dir = self.base_path / "tools" / "build-src"
        out_dir = self.base_path / "tools" / "windows" / "compiled"
        src_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        build_success, build_fail = 0, 0
        total_targets = len(BUILD_TARGETS)

        for i, (name, config) in enumerate(BUILD_TARGETS.items(), 1):
            desc = config.get("description", "")
            self.show_live_status("Building", i, total_targets, f"{name} ({desc[:20]})", "compiling")

            if self.build_dotnet_tool(name, config):
                build_success += 1
                self.stats["ok"] += 1
            else:
                build_fail += 1
                self.stats["fail"] += 1

        self.complete_status_line("C# Build", build_success, build_fail)
        print()

        if build_success > 0:
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} Compiled binaries saved to:{Colors.RESET}")
            print(f"  {Colors.WHITE}  {out_dir}{Colors.RESET}")
            print()

        if build_fail > 0:
            print(f"  {Colors.YELLOW}{Symbols.CIRCLE} {build_fail} tools failed to build.{Colors.RESET}")
            print(f"  {Colors.GRAY}See BUILD_GUIDE.md for manual compilation steps.{Colors.RESET}")
            print()

        self.show_summary()

    def install_windows_binaries(self):
        self.clear_screen()
        self.show_ascii_banner()
        
        print()
        self.print_centered(f"{Colors.NEON_MAGENTA}{Symbols.ROCKET} DOWNLOADING WINDOWS ARSENAL {Symbols.ROCKET}{Colors.RESET}")
        self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
        print()
        
        tools_dir = self.base_path / "tools" / "windows"
        data = TOOL_CATEGORIES.get("Windows Binaries", {})
        tools = data.get("tools", [])
        repos = data.get("repos", [])
        
        # --- Precompiled Binaries ---
        bin_success, bin_fail = 0, 0
        total_tools = len(tools)
        
        def download_bin(item):
            name, method, url, desc = item
            if method == "file": return self.download_file(url, tools_dir / "precompiled" / name)
            elif method == "zip": return self.download_and_extract_zip(url, tools_dir / name.lower())
            elif method == "git": return self.git_clone(url, tools_dir / name)
            return False

        if total_tools > 0:
            completed_bin = 0
            self.show_live_status("Windows Binaries", 0, total_tools, "Starting threads...", "downloading")
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_bin = {executor.submit(download_bin, t): t for t in tools}
                for future in as_completed(future_to_bin):
                    completed_bin += 1
                    if future.result():
                        bin_success += 1
                        self.stats["ok"] += 1
                    else:
                        bin_fail += 1
                        self.stats["fail"] += 1
                    self.show_live_status("Windows Binaries", completed_bin, total_tools, f"Downloading {completed_bin}/{total_tools}", "downloading")
            self.complete_status_line("Windows Binaries", bin_success, bin_fail)
            print()
        
        # --- Git Repositories ---
        repo_success, repo_fail = 0, 0
        total_repos = len(repos)
        
        def clone_repo(item):
            name, url = item
            return self.git_clone(url, tools_dir / name)

        if total_repos > 0:
            completed_repo = 0
            self.show_live_status("Git Repositories", 0, total_repos, "Starting threads...", "cloning")
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_repo = {executor.submit(clone_repo, r): r for r in repos}
                for future in as_completed(future_to_repo):
                    completed_repo += 1
                    if future.result():
                        repo_success += 1
                        self.stats["ok"] += 1
                    else:
                        repo_fail += 1
                        self.stats["fail"] += 1
                    self.show_live_status("Git Repositories", completed_repo, total_repos, f"Cloning {completed_repo}/{total_repos}", "cloning")
            self.complete_status_line("Git Repositories", repo_success, repo_fail)
            print()
            
        self.show_summary()

