"""Kali fix / harden engine — the vendored *pimpmykali* integration.

Surfaces pimpmykali (a 2,900-line, battle-tested "make a fresh Kali VM usable"
script) through VoidWalker's themed UI and single CLI.  We deliberately drive the
proven upstream engine rather than reimplement it: the wrapper stages it into a
writable working directory (it logs + drops temp files into ``cwd``), elevates
with ``sudo`` when needed, and either runs a curated VoidWalker submenu of the
most useful fixes or passes raw flags straight through.

Entry points:
* ``voidwalker kali [--flag ...]``      — CLI (passthrough to pimpmykali switches)
* main-menu *Fix / Harden Kali*         — interactive curated submenu
"""

from __future__ import annotations

import os
import subprocess

from ..theme import Colors, Symbols
from . import stage_pimpmykali


# Curated subset of pimpmykali actions surfaced in VoidWalker's submenu.
# (label, pimpmykali switch | None -> open the full upstream menu)
_KALI_ACTIONS = [
    ("New Kali VM setup (recommended first run)", "--newvm"),
    ("Fix all (menu options 1-8)", "--all"),
    ("Fix missing tools", "--missing"),
    ("Fix nmap scripts", "--nmap"),
    ("Fix smb.conf (LANMAN1)", "--smbconf"),
    ("Install / fix Impacket", "--impacket"),
    ("Install Golang (+ GOPATH)", "--golang"),
    ("Install NetExec (nxc)", "--netexec"),
    ("Enable root login", "--root"),
    ("Pick fastest apt mirrors", "--mirrors"),
    ("Upgrade system (+ guest additions)", "--upgrade"),
    ("Open the full pimpmykali menu", None),
    ("Back to main menu", "__back__"),
]


class KaliFixMixin:
    """Mixed into :class:`~voidwalker.core.VoidWalker`."""

    def _kali_workdir(self):
        return self.base_path / "integrations" / "pimpmykali"

    def _run_pimpmykali(self, args):
        """Stage + execute the vendored pimpmykali engine, streaming its UI.

        ``args`` is a list of pimpmykali CLI switches (empty -> upstream menu).
        Returns the child's exit code (or ``None`` if it could not be launched).
        """
        if not self.is_linux:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} pimpmykali targets Kali/Debian Linux "
                  f"only — not {self.host.label()}.{Colors.RESET}")
            return None

        script = stage_pimpmykali(self._kali_workdir())
        workdir = script.parent

        cmd = ["bash", str(script), *args]
        # pimpmykali requires root (it apt-installs, edits /etc, …); mirror the
        # upstream `sudo ./pimpmykali.sh` usage by elevating when we aren't root.
        is_root = hasattr(os, "geteuid") and os.geteuid() == 0
        if not is_root:
            cmd = ["sudo", *cmd]
            print(f"  {Colors.YELLOW}{Symbols.LIGHTNING} pimpmykali needs root — "
                  f"running under sudo (you may be prompted).{Colors.RESET}")

        shown = " ".join(args) if args else "(interactive menu)"
        print(f"  {Colors.NEON_GREEN}{Symbols.ARROW_RIGHT}{Colors.RESET} "
              f"{Colors.WHITE}pimpmykali {shown}{Colors.RESET}")
        print(f"  {Colors.GRAY}workdir: {workdir}{Colors.RESET}\n")

        try:
            # Inherit stdio so pimpmykali's own prompts/menu drive the terminal.
            proc = subprocess.run(cmd, cwd=str(workdir))
            self.log(f"pimpmykali {shown} exited {proc.returncode}")
            return proc.returncode
        except FileNotFoundError:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} 'sudo'/'bash' not found on PATH.{Colors.RESET}")
            return None
        except KeyboardInterrupt:
            print(f"\n  {Colors.YELLOW}Interrupted.{Colors.RESET}")
            return 130

    def run_kali_fix(self, passthrough=None):
        """CLI entry: ``voidwalker kali [args]``.

        With explicit args, pass them straight to pimpmykali; otherwise drop the
        user into the curated submenu.
        """
        if passthrough:
            return self._run_pimpmykali(list(passthrough))
        return self.kali_fix_menu()

    def kali_fix_menu(self):
        """Interactive, themed submenu of common pimpmykali fixes."""
        while True:
            self.clear_screen()
            self.show_ascii_banner()
            print()
            self.print_centered(
                f"{Colors.NEON_MAGENTA}{Symbols.SHIELD} FIX / HARDEN KALI "
                f"{Colors.GRAY}(pimpmykali engine){Colors.RESET}")
            self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
            print()

            if not self.is_linux:
                self.print_centered(
                    f"{Colors.BRIGHT_RED}Kali/Debian Linux only — current host is "
                    f"{self.host.label()}.{Colors.RESET}")
                print()
                input(f"{Colors.GRAY}Press Enter to return to the main menu...{Colors.RESET}")
                return

            content = []
            for i, (label, _) in enumerate(_KALI_ACTIONS, 1):
                if label == "Back to main menu":
                    content.append(f"{Colors.BRIGHT_RED}[{i:2}] {label}{Colors.RESET}")
                else:
                    content.append(f"{Colors.NEON_CYAN}[{i:2}] {Colors.WHITE}{label}{Colors.RESET}")
            self.draw_box(f"{Symbols.GEAR} KALI FIXES", content, 60)
            print()

            prompt = (f"{Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} "
                      f"Select fix {Colors.GRAY}[1-{len(_KALI_ACTIONS)}]{Colors.RESET}: ")
            try:
                choice = input(prompt).strip()
            except EOFError:
                return
            if not choice.isdigit() or not (1 <= int(choice) <= len(_KALI_ACTIONS)):
                continue

            label, switch = _KALI_ACTIONS[int(choice) - 1]
            if switch == "__back__":
                return

            print()
            args = [] if switch is None else [switch]
            self._run_pimpmykali(args)
            print()
            input(f"{Colors.GRAY}Press Enter to return to the Kali menu...{Colors.RESET}")
