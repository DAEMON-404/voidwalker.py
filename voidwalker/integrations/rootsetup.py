"""Root Setup — give the root account the same experience as the user.

Two long-standing papercuts when you drop into a root shell on a pentest box:

* **The prompt looks identical to your user prompt**, so it's easy to forget you
  are root. This installs the *same two-line prompt, in red* for root.
* **Your tooling "disappears".** netexec, impacket, and friends are installed
  with pipx / go / cargo under your *user* home (``~/.local/bin`` etc.), which
  is not on root's ``$PATH`` — so ``netexec`` as root reports "command not
  found" even though it is right there. This wires the user's toolchains onto
  root's ``$PATH`` (and, optionally, symlinks them into ``/usr/local/bin`` so
  even ``sudo <tool>`` finds them).

Everything is written into clearly delimited *managed blocks* in ``/root/.zshrc``
and ``/root/.bashrc`` so it is idempotent and trivially reversible (delete the
block). The red root prompt itself is produced by the shared
``$PE_CONFIG_DIR/zsh/prompt.zsh``, which switches to a red palette when ``$EUID``
is 0 — so root simply sources the same env the user does.

Entry points:
* ``voidwalker root``            — interactive submenu
* ``voidwalker root setup``      — full setup (prompt + PATH), non-interactive
* ``voidwalker root link``       — also symlink tools into /usr/local/bin
* ``voidwalker root status``     — show what is currently wired up
* main-menu *Root Setup (red prompt + tools)*
"""

from __future__ import annotations

import os
import pwd
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..theme import Colors, Symbols

_ROOT_HOME = Path("/root")
_ROOT_ZSHRC = _ROOT_HOME / ".zshrc"
_ROOT_BASHRC = _ROOT_HOME / ".bashrc"

_BEGIN = "# >>> pentest-env (root) >>>"
_END = "# <<< pentest-env (root) <<<"

_ROOT_ACTIONS = [
    ("Full setup — red root prompt + user tools on root's PATH", "__full__"),
    ("Red root prompt only (zsh)", "__prompt__"),
    ("Expose user tools to root's PATH only (/root/.zshrc + .bashrc)", "__path__"),
    ("Also symlink tools into /usr/local/bin (global; enables sudo <tool>)", "__link__"),
    ("Show root setup status", "__status__"),
    ("Back to main menu", "__back__"),
]

# The POSIX helper that (re)writes a managed block in a target rc file. Run once
# under sudo so it can touch /root. It strips any previous managed block first,
# so re-running is idempotent. $1=rcfile $2=kind(zsh|bash) $3=owner_home $4=cfg_dir
_HELPER = r'''#!/bin/sh
set -eu
rc="$1"; kind="$2"; owner="$3"; cfg="$4"
begin="# >>> pentest-env (root) >>>"
end="# <<< pentest-env (root) <<<"
touch "$rc"
tmp="$(mktemp)"
awk -v b="$begin" -v e="$end" '
  $0==b {skip=1}
  skip==0 {print}
  $0==e {skip=0}
' "$rc" > "$tmp"
{
  cat "$tmp"
  printf '%s\n' "$begin"
  printf 'export PE_OWNER_HOME="%s"\n' "$owner"
  if [ "$kind" = "zsh" ]; then
    printf 'export PE_CONFIG_DIR="%s"\n' "$cfg"
    printf '[ -f "$PE_CONFIG_DIR/zsh/pentest.zsh" ] && source "$PE_CONFIG_DIR/zsh/pentest.zsh"\n'
  else
    printf 'export PATH="$PE_OWNER_HOME/go/bin:$PE_OWNER_HOME/.cargo/bin:$PE_OWNER_HOME/.local/bin:$PE_OWNER_HOME/voidwalker/bin:$PATH"\n'
    # Same two-line shape as the zsh prompt, in red, so bash-as-root is unmistakable.
    printf "PS1='\\[\\e[1;31m\\]\\342\\224\\214\\342\\224\\200[\\u@\\h]\\342\\224\\200[\\w]\\n\\342\\224\\224\\342\\224\\200\\342\\235\\257\\[\\e[0m\\] '\n"
  fi
  printf '%s\n' "$end"
} > "$rc"
rm -f "$tmp"
'''


class RootSetupMixin:
    """Mixed into :class:`~voidwalker.core.VoidWalker`."""

    # ── helpers ─────────────────────────────────────────────────────────────
    def _owner_home(self) -> Path:
        """The *human* user's home whose toolchains we expose to root.

        When VoidWalker itself is run via sudo, ``$HOME`` may already be /root,
        so prefer ``$SUDO_USER``; otherwise use the invoking user's home.
        """
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            try:
                return Path(pwd.getpwnam(sudo_user).pw_dir)
            except KeyError:
                pass
        home = Path.home()
        if home == _ROOT_HOME:
            # Running as real root with no SUDO_USER — fall back to the checkout
            # that owns this pentest-env config, if we can find one.
            for base in ("/home",):
                for cand in sorted(Path(base).glob("*/.config/pentest-env")):
                    return cand.parent.parent
        return home

    def _pe_config_dir(self, owner_home: Path) -> Path:
        return owner_home / ".config" / "pentest-env"

    def _root_run(self, cmd, desc: str = "") -> bool:
        """Run *cmd* as root (prefixing sudo when we aren't already root).

        Uses an inheriting stdio (no capture) so an interactive sudo password
        prompt actually reaches the user's terminal.
        """
        is_root = hasattr(os, "geteuid") and os.geteuid() == 0
        full = list(cmd) if is_root else ["sudo", *cmd]
        if desc:
            print(f"  {Colors.GRAY}$ {' '.join(full)}{Colors.RESET}")
        try:
            return subprocess.run(full).returncode == 0
        except FileNotFoundError:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} '{full[0]}' not found on PATH.{Colors.RESET}")
            return False
        except KeyboardInterrupt:
            print(f"  {Colors.YELLOW}Aborted.{Colors.RESET}")
            return False

    def _write_root_block(self, kind: str, owner_home: Path, cfg_dir: Path) -> bool:
        """Install/refresh the managed block in /root/.{zshrc,bashrc}."""
        rc = _ROOT_ZSHRC if kind == "zsh" else _ROOT_BASHRC
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tf:
            tf.write(_HELPER)
            helper = tf.name
        os.chmod(helper, 0o755)
        try:
            ok = self._root_run(
                ["sh", helper, str(rc), kind, str(owner_home), str(cfg_dir)],
                desc=f"install {kind} root block → {rc}",
            )
        finally:
            os.unlink(helper)
        if ok:
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} {rc} updated.{Colors.RESET}")
        else:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} failed to update {rc}.{Colors.RESET}")
        return ok

    def _set_root_shell_zsh(self) -> None:
        """Best-effort: make root's login shell zsh so `sudo -i` / `su -` are red."""
        zsh = shutil.which("zsh")
        if not zsh:
            print(f"  {Colors.YELLOW}{Symbols.CIRCLE} zsh not found — skipping root login-shell change.{Colors.RESET}")
            return
        try:
            current = pwd.getpwnam("root").pw_shell
        except KeyError:
            current = ""
        if current == zsh:
            print(f"  {Colors.GRAY}root login shell already zsh.{Colors.RESET}")
            return
        if self._root_run(["chsh", "-s", zsh, "root"], desc="set root login shell → zsh"):
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} root login shell set to {zsh}.{Colors.RESET}")
        else:
            print(f"  {Colors.YELLOW}{Symbols.CIRCLE} could not change root's login shell "
                  f"(you can still use `sudo zsh`).{Colors.RESET}")

    # ── high-level actions ──────────────────────────────────────────────────
    def _do_path(self, owner_home: Path, cfg_dir: Path) -> bool:
        print(f"  {Colors.NEON_CYAN}Exposing {owner_home}'s toolchains to root…{Colors.RESET}")
        ok_z = self._write_root_block("zsh", owner_home, cfg_dir)
        ok_b = self._write_root_block("bash", owner_home, cfg_dir)
        if ok_z or ok_b:
            print(f"  {Colors.GRAY}Open a new root shell (e.g. `sudo -i`) — netexec, impacket, "
                  f"go/cargo tools will be on PATH.{Colors.RESET}")
        return ok_z and ok_b

    def _do_prompt(self, cfg_dir: Path, owner_home: Path) -> bool:
        prompt_zsh = cfg_dir / "zsh" / "prompt.zsh"
        if not prompt_zsh.is_file():
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} {prompt_zsh} not found — deploy the "
                  f"Pentest Environment (pe) first.{Colors.RESET}")
            return False
        # The red palette lives in the shared prompt.zsh (EUID 0 branch); root
        # gets it simply by sourcing the env, which the zsh block wires up.
        ok = self._write_root_block("zsh", owner_home, cfg_dir)
        self._set_root_shell_zsh()
        if ok:
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} Red root prompt wired up.{Colors.RESET} "
                  f"{Colors.GRAY}Start a root shell to see it.{Colors.RESET}")
        return ok

    def _do_link(self, owner_home: Path) -> bool:
        """Symlink user-local tool binaries into /usr/local/bin (global)."""
        target = Path("/usr/local/bin")
        srcs = [owner_home / ".local" / "bin", owner_home / "go" / "bin",
                owner_home / ".cargo" / "bin", owner_home / "voidwalker" / "bin"]
        names: dict[str, Path] = {}
        for d in srcs:
            if not d.is_dir():
                continue
            for f in sorted(d.iterdir()):
                if not f.name.startswith(".") and os.access(f, os.X_OK) and not f.is_dir():
                    names.setdefault(f.name, f)  # first source wins (matches PATH order)
        if not names:
            print(f"  {Colors.YELLOW}No user-local tool binaries found under {owner_home}.{Colors.RESET}")
            return False
        # Skip names already provided by a *real* system binary so we never
        # shadow the OS toolchain; a prior symlink of ours is fine to refresh.
        plan, skipped = [], []
        for name, src in names.items():
            dest = target / name
            if dest.exists() and not dest.is_symlink():
                skipped.append(name)
                continue
            plan.append((name, src, dest))
        print(f"  {Colors.NEON_CYAN}Linking {len(plan)} tool(s) into {target}"
              f"{f' ({len(skipped)} skipped — real system binary)' if skipped else ''}…{Colors.RESET}")
        if not plan:
            return True
        # One sudo invocation: feed a tiny script the whole link plan.
        lines = ["#!/bin/sh", "set -eu"]
        for _name, src, dest in plan:
            lines.append(f'ln -sfn "{src}" "{dest}"')
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tf:
            tf.write("\n".join(lines) + "\n")
            helper = tf.name
        os.chmod(helper, 0o755)
        try:
            ok = self._root_run(["sh", helper], desc=f"symlink {len(plan)} tools → {target}")
        finally:
            os.unlink(helper)
        if ok:
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} {len(plan)} tool(s) linked "
                  f"(e.g. `sudo netexec` now works).{Colors.RESET}")
        return ok

    def _show_status(self, owner_home: Path, cfg_dir: Path) -> None:
        c, g, w = Colors.NEON_CYAN, Colors.GRAY, Colors.WHITE
        print(f"  {c}Owner home:{Colors.RESET} {w}{owner_home}{Colors.RESET}")
        print(f"  {c}pentest-env:{Colors.RESET} {w}{cfg_dir}{Colors.RESET} "
              f"{self._mark((cfg_dir / 'zsh' / 'prompt.zsh').is_file())}")

        def _block_state(rc: Path) -> str:
            try:
                txt = rc.read_text()
            except (OSError, PermissionError):
                return f"{Colors.YELLOW}unreadable (need root to inspect){Colors.RESET}"
            return self._mark(_BEGIN in txt) if rc.exists() else f"{g}absent{Colors.RESET}"

        print(f"  {c}/root/.zshrc block:{Colors.RESET} {_block_state(_ROOT_ZSHRC)}")
        print(f"  {c}/root/.bashrc block:{Colors.RESET} {_block_state(_ROOT_BASHRC)}")
        try:
            root_shell = pwd.getpwnam("root").pw_shell
        except KeyError:
            root_shell = "?"
        is_zsh = root_shell.endswith("zsh")
        print(f"  {c}root login shell:{Colors.RESET} {w}{root_shell}{Colors.RESET} "
              f"{self._mark(is_zsh)}")
        nxc = shutil.which("nxc") or shutil.which("netexec") \
            or ((owner_home / ".local/bin/netexec").is_file() and str(owner_home / ".local/bin/netexec"))
        print(f"  {c}netexec (nxc):{Colors.RESET} {w}{nxc or 'not found'}{Colors.RESET} {self._mark(bool(nxc))}")

    def _mark(self, ok: bool) -> str:
        return (f"{Colors.NEON_GREEN}{Symbols.CHECK}{Colors.RESET}" if ok
                else f"{Colors.BRIGHT_RED}{Symbols.CROSS}{Colors.RESET}")

    # ── entry points ────────────────────────────────────────────────────────
    def run_root_setup(self, passthrough=None):
        """CLI entry: ``voidwalker root [setup|prompt|path|link|status]``."""
        owner_home = self._owner_home()
        cfg_dir = self._pe_config_dir(owner_home)
        sub = (passthrough[0].lower() if passthrough else "")
        if sub in ("setup", "full", ""):
            if not sub:
                return self.root_setup_menu()
            self._do_path(owner_home, cfg_dir)
            self._set_root_shell_zsh()
            return 0
        if sub == "prompt":
            self._do_prompt(cfg_dir, owner_home); return 0
        if sub == "path":
            self._do_path(owner_home, cfg_dir); return 0
        if sub == "link":
            self._do_link(owner_home); return 0
        if sub == "status":
            self._show_status(owner_home, cfg_dir); return 0
        print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} unknown 'root' subcommand "
              f"'{sub}'. Use setup/prompt/path/link/status.{Colors.RESET}")
        return 1

    def root_setup_menu(self):
        owner_home = self._owner_home()
        cfg_dir = self._pe_config_dir(owner_home)
        while True:
            self.clear_screen()
            self.show_ascii_banner()
            print()
            self.print_centered(
                f"{Colors.BRIGHT_RED}{Symbols.SHIELD} ROOT SETUP "
                f"{Colors.GRAY}(red prompt + your tools as root){Colors.RESET}")
            self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
            print()

            content = []
            for i, (label, _) in enumerate(_ROOT_ACTIONS, 1):
                if label.startswith("Back"):
                    content.append(f"{Colors.BRIGHT_RED}[{i}] {label}{Colors.RESET}")
                else:
                    content.append(f"{Colors.NEON_CYAN}[{i}] {Colors.WHITE}{label}{Colors.RESET}")
            self.draw_box(f"{Symbols.SHIELD} ROOT SETUP", content, 66)
            print()

            prompt = (f"{Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} "
                      f"Select option {Colors.GRAY}[1-{len(_ROOT_ACTIONS)}]{Colors.RESET}: ")
            try:
                choice = input(prompt).strip()
            except EOFError:
                return
            if not choice.isdigit() or not (1 <= int(choice) <= len(_ROOT_ACTIONS)):
                continue

            _label, action = _ROOT_ACTIONS[int(choice) - 1]
            if action == "__back__":
                return

            print()
            if action == "__full__":
                self._do_path(owner_home, cfg_dir)
                print()
                self._do_prompt(cfg_dir, owner_home)
            elif action == "__prompt__":
                self._do_prompt(cfg_dir, owner_home)
            elif action == "__path__":
                self._do_path(owner_home, cfg_dir)
            elif action == "__link__":
                self._do_link(owner_home)
            elif action == "__status__":
                self._show_status(owner_home, cfg_dir)

            print()
            input(f"{Colors.GRAY}Press Enter to return to the root setup menu...{Colors.RESET}")
