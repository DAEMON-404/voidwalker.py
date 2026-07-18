"""Pentest environment — the vendored *pentest-env* integration.

Folds the ``pe`` toolkit (an encrypted, target-centric store for flags / creds /
hosts / notes, plus the Rose Pine ZSH/tmux desktop profiles and the ``pe cheat``
cheatsheets) into VoidWalker.  Two surfaces:

* ``voidwalker env [install flags]`` / main-menu *Deploy Pentest Environment* —
  runs the vendored ``install.sh``. This is the *install*: it deploys to
  ``~/.config/pentest-env``, symlinks a **standalone** ``pe`` onto
  ``~/.local/bin``, wires ``~/.zshrc`` / ``~/.tmux.conf``, installs the offline
  HTML handbook, and runs ``pe init``. Ubuntu GNOME receives a rollback-safe
  Rose Pine desktop preset; XFCE and optional BSPWM remain supported.
  Afterwards ``pe …`` works on its own, with no ``voidwalker`` prefix.
* ``voidwalker pe <noun> <verb> ...`` — a thin passthrough to the ``pe``
  dispatcher so the encrypted workspace is usable straight from VoidWalker,
  whether or not ``install.sh`` has run yet (it falls back to the vendored copy,
  which writes the *same* ``$XDG`` encrypted DB a deployed ``pe`` would).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..theme import Colors, Symbols
from . import PENTEST_ENV_DIR, PENTEST_ENV_INSTALLER, PENTEST_ENV_PE, PENTEST_ENV_PT


# (label, install.sh args | sentinel)
_ENV_ACTIONS = [
    ("Full install (pe + zsh + tmux + Rose Pine desktop + HTML handbook)", []),
    ("Core only (skip desktop theming + BSPWM rice)", ["--no-wm", "--no-theme"]),
    ("Preview install — dry-run, change nothing", ["--dry-run"]),
    ("Install Parallels Tools (Kali guest; attach the Tools CD first)", "__pt__"),
    ("Uninstall integration (keeps your encrypted DB)", ["--uninstall"]),
    ("Open the pe workspace manager (pe help)", "__pe__"),
    ("Back to main menu", "__back__"),
]


class PentestEnvMixin:
    """Mixed into :class:`~voidwalker.core.VoidWalker`."""

    # ── install.sh driver ──────────────────────────────────────────────────
    def _run_env_installer(self, args):
        """Run the vendored pentest-env ``install.sh`` (streams its output)."""
        if not (self.is_linux or self.is_macos):
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} pentest-env supports Linux & macOS "
                  f"only — not {self.host.label()}.{Colors.RESET}")
            return None

        cmd = ["bash", str(PENTEST_ENV_INSTALLER), *args]
        shown = " ".join(args) if args else "(full install)"
        print(f"  {Colors.NEON_GREEN}{Symbols.ARROW_RIGHT}{Colors.RESET} "
              f"{Colors.WHITE}pentest-env install {shown}{Colors.RESET}")
        if "--dry-run" not in args and "--uninstall" not in args:
            print(f"  {Colors.GRAY}Deploys to ~/.config/pentest-env and wires "
                  f"~/.zshrc + ~/.tmux.conf. You'll set a DB key passphrase.{Colors.RESET}")
        print()
        try:
            # install.sh only reads its payload, so running it in-place (even from
            # a read-only package dir) is safe; it writes solely under $HOME.
            proc = subprocess.run(cmd, cwd=str(PENTEST_ENV_DIR))
            self.log(f"pentest-env install {shown} exited {proc.returncode}")
            return proc.returncode
        except FileNotFoundError:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} 'bash' not found on PATH.{Colors.RESET}")
            return None
        except KeyboardInterrupt:
            print(f"\n  {Colors.YELLOW}Interrupted.{Colors.RESET}")
            return 130

    def deploy_pentest_env(self, passthrough=None):
        """CLI entry: ``voidwalker env [args]`` (else the interactive submenu)."""
        if passthrough:
            return self._run_env_installer(list(passthrough))
        return self.pentest_env_menu()

    def pentest_env_menu(self):
        """Interactive, themed submenu for deploying / managing pentest-env."""
        while True:
            self.clear_screen()
            self.show_ascii_banner()
            print()
            self.print_centered(
                f"{Colors.NEON_MAGENTA}{Symbols.SHIELD} DEPLOY PENTEST ENVIRONMENT "
                f"{Colors.GRAY}(pe toolkit){Colors.RESET}")
            self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
            print()

            content = []
            for i, (label, _) in enumerate(_ENV_ACTIONS, 1):
                if label == "Back to main menu":
                    content.append(f"{Colors.BRIGHT_RED}[{i}] {label}{Colors.RESET}")
                else:
                    content.append(f"{Colors.NEON_CYAN}[{i}] {Colors.WHITE}{label}{Colors.RESET}")
            self.draw_box(f"{Symbols.GEAR} PENTEST-ENV", content, 64)
            print()

            prompt = (f"{Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} "
                      f"Select option {Colors.GRAY}[1-{len(_ENV_ACTIONS)}]{Colors.RESET}: ")
            try:
                choice = input(prompt).strip()
            except EOFError:
                return
            if not choice.isdigit() or not (1 <= int(choice) <= len(_ENV_ACTIONS)):
                continue

            label, action = _ENV_ACTIONS[int(choice) - 1]
            if action == "__back__":
                return

            print()
            if action == "__pe__":
                self.run_pe(["help"])
            elif action == "__pt__":
                self.run_parallels_tools([])
            else:
                self._run_env_installer(action)
            print()
            input(f"{Colors.GRAY}Press Enter to return to the pentest-env menu...{Colors.RESET}")

    # ── Parallels Tools helper ─────────────────────────────────────────────
    def run_parallels_tools(self, args=None):
        """CLI/menu entry: install Parallels Tools in a Kali guest.

        Runs the vendored ``parallels-tools.sh`` helper (preferring a deployed
        ``pt-install`` if present).  The helper *self-elevates* with sudo, so we
        deliberately do **not** wrap it — its own header warns that running it
        under sudo breaks because ``~/.local/bin`` isn't on sudo's secure_path.
        Pass ``--mount-only`` / ``--no-deps`` / ``--help`` straight through.
        """
        args = list(args or [])
        if not self.is_linux:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} Parallels Tools installs inside the "
                  f"Kali *guest*, not on a {self.host.label()} host.{Colors.RESET}")
            return None

        installed = Path.home() / ".local" / "bin" / "pt-install"
        if installed.exists():
            prefix = [str(installed)]
        elif shutil.which("pt-install"):
            prefix = [shutil.which("pt-install")]
        else:
            prefix = ["bash", str(PENTEST_ENV_PT)]

        print(f"  {Colors.NEON_GREEN}{Symbols.ARROW_RIGHT}{Colors.RESET} "
              f"{Colors.WHITE}Parallels Tools installer{Colors.RESET} "
              f"{Colors.GRAY}(self-elevates with sudo){Colors.RESET}")
        print(f"  {Colors.YELLOW}Attach the CD first: Parallels menu → Actions → "
              f"Install Parallels Tools.{Colors.RESET}\n")
        try:
            proc = subprocess.run([*prefix, *args])
            self.log(f"parallels-tools {' '.join(args)} exited {proc.returncode}")
            return proc.returncode
        except FileNotFoundError:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} could not launch the Parallels helper.{Colors.RESET}")
            return None
        except KeyboardInterrupt:
            print(f"\n  {Colors.YELLOW}Interrupted.{Colors.RESET}")
            return 130

    # ── pe dispatcher passthrough ──────────────────────────────────────────
    def _pe_command(self):
        """Resolve which ``pe`` to run: a deployed one wins, else the vendored copy.

        Returns ``(cmd_prefix, env, vendored)`` where *cmd_prefix* is the argv
        prefix the ``pe`` sub-arguments get appended to, and *vendored* is True
        when we fell back to the bundled copy (i.e. ``pe`` isn't installed yet).
        """
        env = os.environ.copy()
        installed = Path.home() / ".local" / "bin" / "pe"
        if installed.exists():
            return [str(installed)], env, False
        on_path = shutil.which("pe")
        if on_path:
            return [on_path], env, False
        # Fall back to the vendored dispatcher; PE_CONFIG_DIR resolves from its
        # own location, and the data/state dirs live under $XDG (writable), so
        # the encrypted DB is the *same* one a deployed `pe` would use.
        return ["bash", str(PENTEST_ENV_PE)], env, True

    def run_pe(self, args):
        """CLI entry: ``voidwalker pe <args...>`` — passthrough to ``pe``."""
        if not (self.is_linux or self.is_macos):
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} the pe workspace supports Linux & macOS "
                  f"only — not {self.host.label()}.{Colors.RESET}")
            return None

        prefix, env, vendored = self._pe_command()
        # Using the bundled pe works, but the *standalone* `pe` command and the
        # shell prompt / tmux bar / cheatsheets only exist after a deploy. Nudge
        # the user — on stderr, TTY-only, so it never pollutes scripted output.
        if vendored and sys.stderr.isatty():
            print(f"{Colors.GRAY}(using the bundled pe — run 'voidwalker env' to install "
                  f"'pe' as a standalone command + shell integration){Colors.RESET}",
                  file=sys.stderr)
        cmd = [*prefix, *list(args)]
        try:
            proc = subprocess.run(cmd, env=env)
            return proc.returncode
        except FileNotFoundError:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} could not launch pe "
                  f"({' '.join(prefix)}).{Colors.RESET}")
            print(f"  {Colors.GRAY}Run 'voidwalker env' first to deploy the toolkit.{Colors.RESET}")
            return None
        except KeyboardInterrupt:
            return 130
