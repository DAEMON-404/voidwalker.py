"""BloodHound Community Edition — guided install + first-run setup.

Surfaces BloodHound CE through VoidWalker's themed UI / single CLI by driving the
official **`bloodhound-cli`** binary (SpecterOps), downloaded from GitHub Releases
per OS/arch. `bloodhound-cli` orchestrates the Docker stack (Postgres + Neo4j +
BloodHound), so the one prerequisite is Docker — which this mixin will auto-install
on Linux (Debian/Kali) or guide you to install on macOS.

Entry points:
* ``voidwalker bloodhound``            — interactive submenu (install / start / stop / …)
* ``voidwalker bloodhound <args...>``  — passthrough to the raw bloodhound-cli binary
* main-menu *Setup BloodHound-CE*

Pure Python — no vendored asset (the binary is fetched on demand), so there are no
packaging changes.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from ..theme import Colors, Symbols


# bloodhound-cli release assets (GitHub `latest/download` resolves these by name,
# the same pattern the tool catalog already relies on).
_BHCLI_BASE = "https://github.com/SpecterOps/bloodhound-cli/releases/latest/download"
BHCLI_ASSETS = {
    ("linux", "amd64"): "bloodhound-cli-linux-amd64.tar.gz",
    ("linux", "arm64"): "bloodhound-cli-linux-arm64.tar.gz",
    ("darwin", "amd64"): "bloodhound-cli-darwin-amd64.tar.gz",
    ("darwin", "arm64"): "bloodhound-cli-darwin-arm64.tar.gz",
    ("windows", "amd64"): "bloodhound-cli-windows-amd64.zip",
}
BH_UI_URL = "http://localhost:8080/ui/login"
_BH_HOST = "http://localhost:8080"


def bh_asset_for(host):
    """Return the bloodhound-cli asset filename for *host*, or None if unsupported."""
    return BHCLI_ASSETS.get((host.os, host.arch))


# (label, action) — action is a sentinel string or a literal bloodhound-cli argv list.
_BLOODHOUND_ACTIONS = [
    ("Install & start BloodHound-CE  (first run)", "__install__"),
    ("Start containers", ["containers", "up"]),
    ("Stop containers", ["containers", "stop"]),
    ("Get admin password", "__passwd__"),
    ("Open the web UI  (http://localhost:8080)", "__open__"),
    ("Data collectors  (SharpHound / AzureHound / bloodhound-ce-python)", "__collectors__"),
    ("Run a raw bloodhound-cli command…", "__raw__"),
    ("Uninstall  (stop & remove containers)", ["containers", "down"]),
    ("Back to main menu", "__back__"),
]


class BloodHoundMixin:
    """Mixed into :class:`~voidwalker.core.VoidWalker`."""

    # ── binary acquisition ─────────────────────────────────────────────────
    def _bh_workdir(self):
        return self.base_path / "integrations" / "bloodhound"

    def _bh_binary(self):
        name = "bloodhound-cli.exe" if self.host.is_windows else "bloodhound-cli"
        return self._bh_workdir() / name

    def _ensure_bhcli(self):
        """Download + extract the bloodhound-cli binary for this host. Returns path/None."""
        binary = self._bh_binary()
        if binary.exists():
            return binary
        asset = bh_asset_for(self.host)
        if not asset:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} no bloodhound-cli build for "
                  f"{self.host.label()} — unsupported architecture.{Colors.RESET}")
            return None
        workdir = self._bh_workdir()
        workdir.mkdir(parents=True, exist_ok=True)
        url = f"{_BHCLI_BASE}/{asset}"
        print(f"  {Colors.YELLOW}Downloading bloodhound-cli ({asset})…{Colors.RESET}")
        ok = (self.download_and_extract_zip(url, workdir) if asset.endswith(".zip")
              else self._download_and_extract_tar_gz(url, workdir, "bloodhound-cli"))
        if not ok or not binary.exists():
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} failed to fetch bloodhound-cli "
                  f"from {url}{Colors.RESET}")
            return None
        try:
            binary.chmod(0o755)
        except OSError:
            pass
        print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} bloodhound-cli ready: {binary}{Colors.RESET}")
        return binary

    # ── Docker prerequisite ────────────────────────────────────────────────
    def _have_docker(self):
        return bool(shutil.which("docker")) and self.run_cmd(["docker", "compose", "version"], timeout=30)

    def _ensure_docker(self):
        """Ensure Docker Engine + Compose v2. Auto-installs on Linux; guides on macOS."""
        if self._have_docker():
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} Docker + compose detected.{Colors.RESET}")
            return True
        if self.is_macos:
            print(f"  {Colors.YELLOW}Docker not found — install Docker Desktop for macOS:{Colors.RESET}")
            print(f"  {Colors.WHITE}  https://www.docker.com/products/docker-desktop/{Colors.RESET}")
            return False
        if not self.is_linux:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} Docker auto-install is Linux-only.{Colors.RESET}")
            return False
        print(f"  {Colors.YELLOW}{Symbols.LIGHTNING} Docker not found — installing "
              f"docker.io + docker-compose-plugin (sudo)…{Colors.RESET}")
        self.run_cmd(["sudo", "apt-get", "update"], timeout=300)
        if not self.run_cmd(["sudo", "apt-get", "install", "-y",
                             "docker.io", "docker-compose-plugin"], timeout=900):
            # the compose-plugin package name varies across releases; try the v2 alias
            self.run_cmd(["sudo", "apt-get", "install", "-y", "docker-compose-v2"], timeout=300)
        self.run_cmd(["sudo", "systemctl", "enable", "--now", "docker"], timeout=120)
        user = os.environ.get("SUDO_USER") or os.environ.get("USER") or ""
        if user and user != "root":
            self.run_cmd(["sudo", "usermod", "-aG", "docker", user], timeout=60)
            print(f"  {Colors.GRAY}Added '{user}' to the docker group — log out/in for it to take "
                  f"effect (until then this may need root).{Colors.RESET}")
        if self._have_docker():
            print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} Docker installed.{Colors.RESET}")
            return True
        print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} Docker still unavailable — install it "
              f"manually then retry: https://docs.docker.com/engine/install/{Colors.RESET}")
        return False

    # ── bloodhound-cli execution ───────────────────────────────────────────
    def _run_bhcli(self, args, capture=False):
        """Run bloodhound-cli. Returns rc (streamed), a CompletedProcess (capture), or None."""
        binary = self._ensure_bhcli()
        if not binary:
            return None
        cmd = [str(binary), *args]
        workdir = str(self._bh_workdir())
        try:
            if capture:
                return subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
            proc = subprocess.run(cmd, cwd=workdir)
            self.log(f"bloodhound-cli {' '.join(args)} exited {proc.returncode}")
            return proc.returncode
        except FileNotFoundError:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} could not execute bloodhound-cli.{Colors.RESET}")
            return None
        except KeyboardInterrupt:
            print(f"\n  {Colors.YELLOW}Interrupted.{Colors.RESET}")
            return 130

    # ── high-level flows ───────────────────────────────────────────────────
    def bloodhound_install_and_start(self):
        """Guided first run: fetch binary → ensure Docker → install → up → show creds."""
        if not (self.is_linux or self.is_macos):
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} run BloodHound-CE from a Linux/macOS attack "
                  f"host, not {self.host.label()}.{Colors.RESET}")
            return
        if not self._ensure_bhcli():
            return
        if not self._ensure_docker():
            print(f"  {Colors.YELLOW}Docker is required for BloodHound-CE — aborting.{Colors.RESET}")
            return
        print(f"\n  {Colors.NEON_MAGENTA}{Symbols.ROCKET} Installing BloodHound-CE "
              f"(pulls Postgres + Neo4j + BloodHound images, first run is slow)…{Colors.RESET}\n")
        rc = self._run_bhcli(["install"])
        if rc not in (0, None):
            print(f"  {Colors.YELLOW}{Symbols.CIRCLE} 'bloodhound-cli install' returned {rc}; "
                  f"trying 'containers up'.{Colors.RESET}")
        self._run_bhcli(["containers", "up"])
        self.guided_first_run()

    def _bh_admin_password(self):
        """Best-effort retrieval of the generated admin password via `config get`.

        Returns ``(password_or_None, raw_output_or_None)`` so the caller can fall
        back to showing the full config if the exact field name ever changes.
        """
        proc = self._run_bhcli(["config", "get"], capture=True)
        if not proc:
            return None, None
        out = ((proc.stdout or "") + (proc.stderr or "")).strip()
        pw = None
        for line in out.splitlines():
            if "password" in line.lower():
                for sep in ("=", ":"):
                    if sep in line:
                        cand = line.split(sep, 1)[1].strip().strip('"').strip()
                        if cand:
                            pw = cand
                        break
        return pw, out

    def guided_first_run(self):
        """vault.py-style summary: print URL, admin user + password, and next steps."""
        pw, raw = self._bh_admin_password()
        print()
        lines = [
            f"{Colors.NEON_GREEN}{Symbols.CHECK} BloodHound-CE is up.{Colors.RESET}",
            f"{Colors.ELECTRIC_BLUE}URL :{Colors.RESET} {Colors.WHITE}{BH_UI_URL}{Colors.RESET}",
            f"{Colors.ELECTRIC_BLUE}User:{Colors.RESET} {Colors.WHITE}admin{Colors.RESET}",
        ]
        if pw:
            lines.append(f"{Colors.ELECTRIC_BLUE}Pass:{Colors.RESET} {Colors.NEON_GREEN}{pw}{Colors.RESET}")
        else:
            lines.append(f"{Colors.YELLOW}Pass: use 'Get admin password' (config get){Colors.RESET}")
        self.draw_box(f"{Symbols.SHIELD} BLOODHOUND-CE READY", lines, 60)
        print()
        if not pw and raw:
            print(f"  {Colors.GRAY}bloodhound-cli config get:{Colors.RESET}\n{raw}\n")
        print(f"  {Colors.NEON_CYAN}Next steps:{Colors.RESET}")
        print(f"   {Colors.WHITE}1.{Colors.RESET} Open {BH_UI_URL}, log in as admin, "
              f"change the password on first login.")
        print(f"   {Colors.WHITE}2.{Colors.RESET} Collect AD data (SharpHound / bloodhound-ce-python / "
              f"AzureHound) — see the 'Data collectors' menu item.")
        print(f"   {Colors.WHITE}3.{Colors.RESET} Upload the resulting .zip in the UI: "
              f"Administration → File Ingest.")
        print()
        self._open_ui()

    def _open_ui(self):
        print(f"  {Colors.ELECTRIC_BLUE}BloodHound UI:{Colors.RESET} {Colors.WHITE}{BH_UI_URL}{Colors.RESET}")
        opener = "open" if self.is_macos else "xdg-open"
        if shutil.which(opener):
            try:
                subprocess.Popen([opener, _BH_HOST],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"  {Colors.GRAY}(opening in your browser…){Colors.RESET}")
            except OSError:
                pass

    def _bh_collectors_info(self):
        base = self.base_path / "tools"
        print(f"  {Colors.NEON_CYAN}BloodHound-CE data collectors (install via the arsenal, then run):{Colors.RESET}")
        print(f"   {Colors.WHITE}SharpHound{Colors.RESET} {Colors.GRAY}(Windows/.NET — {base / 'ad' / 'bloodhound'}){Colors.RESET}")
        print(f"      {Colors.GRAY}SharpHound.exe -c All --zipfilename loot{Colors.RESET}")
        print(f"   {Colors.WHITE}bloodhound-ce-python{Colors.RESET} {Colors.GRAY}(no Windows needed — UV tool){Colors.RESET}")
        print(f"      {Colors.GRAY}bloodhound-ce-python -u user -p pass -d domain.local -ns <DC-IP> -c All{Colors.RESET}")
        print(f"   {Colors.WHITE}AzureHound{Colors.RESET} {Colors.GRAY}(Entra ID — Cloud Tools → AzureHound){Colors.RESET}")
        print(f"      {Colors.GRAY}azurehound list -u user -p pass -t <tenant> -o output.json{Colors.RESET}")
        print(f"  {Colors.GRAY}Upload outputs in the UI: Administration → File Ingest.{Colors.RESET}")

    # ── CLI + menu entry points ────────────────────────────────────────────
    def run_bloodhound(self, passthrough=None):
        """CLI entry: ``voidwalker bloodhound [args]`` — raw passthrough or menu."""
        if passthrough:
            rc = self._run_bhcli(list(passthrough))
            return rc if isinstance(rc, int) else 0
        return self.bloodhound_menu()

    def bloodhound_menu(self):
        """Interactive, themed BloodHound-CE submenu."""
        while True:
            self.clear_screen()
            self.show_ascii_banner()
            print()
            self.print_centered(
                f"{Colors.NEON_MAGENTA}{Symbols.SHIELD} BLOODHOUND-CE "
                f"{Colors.GRAY}(SpecterOps bloodhound-cli){Colors.RESET}")
            self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
            print()

            if not (self.is_linux or self.is_macos):
                self.print_centered(f"{Colors.BRIGHT_RED}Linux/macOS only — current host is "
                                    f"{self.host.label()}.{Colors.RESET}")
                print()
                input(f"{Colors.GRAY}Press Enter to return to the main menu...{Colors.RESET}")
                return

            content = []
            for i, (label, _) in enumerate(_BLOODHOUND_ACTIONS, 1):
                if label.startswith("Back"):
                    content.append(f"{Colors.BRIGHT_RED}[{i}] {label}{Colors.RESET}")
                else:
                    content.append(f"{Colors.NEON_CYAN}[{i}] {Colors.WHITE}{label}{Colors.RESET}")
            self.draw_box(f"{Symbols.GEAR} BLOODHOUND-CE", content, 66)
            print()

            prompt = (f"{Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} "
                      f"Select option {Colors.GRAY}[1-{len(_BLOODHOUND_ACTIONS)}]{Colors.RESET}: ")
            try:
                choice = input(prompt).strip()
            except EOFError:
                return
            if not choice.isdigit() or not (1 <= int(choice) <= len(_BLOODHOUND_ACTIONS)):
                continue

            label, action = _BLOODHOUND_ACTIONS[int(choice) - 1]
            if action == "__back__":
                return

            print()
            if action == "__install__":
                self.bloodhound_install_and_start()
            elif action == "__passwd__":
                pw, raw = self._bh_admin_password()
                if pw:
                    print(f"  {Colors.ELECTRIC_BLUE}admin password:{Colors.RESET} "
                          f"{Colors.NEON_GREEN}{pw}{Colors.RESET}")
                elif raw:
                    print(raw)
                else:
                    print(f"  {Colors.YELLOW}Couldn't read it — is BloodHound installed & running?{Colors.RESET}")
            elif action == "__open__":
                self._open_ui()
            elif action == "__collectors__":
                self._bh_collectors_info()
            elif action == "__raw__":
                try:
                    raw_args = input(f"  {Colors.NEON_MAGENTA}bloodhound-cli{Colors.RESET} ").strip()
                except EOFError:
                    raw_args = ""
                if raw_args:
                    self._run_bhcli(raw_args.split())
            elif isinstance(action, list):
                self._run_bhcli(action)

            print()
            input(f"{Colors.GRAY}Press Enter to return to the BloodHound menu...{Colors.RESET}")
