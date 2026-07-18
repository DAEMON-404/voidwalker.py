"""Proxy / pivot helper — a thin, safe wrapper around proxychains4.

Engagements pivot through layers (external host → SOCKS → internal AD), and
every tool needs the same proxy wired up. This writes a managed proxychains
config to ``~/.proxychains/proxychains.conf`` — which proxychains4 reads *before*
``/etc/proxychains4.conf`` — so we never touch a system file or need root, and
the change is per-user and reversible (just delete the file).

Entry points:
* ``voidwalker proxy``              — interactive submenu
* ``voidwalker proxy <host:port>``  — set the SOCKS proxy directly (e.g. 127.0.0.1:1080)
* main-menu *Proxy / Pivot helper*

Pair it with a tunnel: ``ssh -D 1080 user@pivot``, chisel, or ligolo-ng (the
arsenal installs the latter two), then prefix tools with ``proxychains4``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..theme import Colors, Symbols

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 1080

_PROXY_ACTIONS = [
    ("Set SOCKS proxy (write ~/.proxychains/proxychains.conf)", "__set__"),
    ("Show current proxychains config", "__show__"),
    ("Pivot / tunnel cheatsheet (ssh -D, chisel, ligolo-ng)", "__cheat__"),
    ("Back to main menu", "__back__"),
]


class ProxyMixin:
    """Mixed into :class:`~voidwalker.core.VoidWalker`."""

    def _proxychains_conf(self):
        return Path.home() / ".proxychains" / "proxychains.conf"

    def _parse_socks(self, spec):
        """Parse 'host:port' or bare 'port' → (host, port:int) or (None, None)."""
        spec = spec.strip()
        if ":" in spec:
            host, _, port = spec.rpartition(":")
            host = host or _DEFAULT_HOST
        else:
            host, port = _DEFAULT_HOST, spec
        if not port.isdigit() or not (0 < int(port) < 65536):
            return None, None
        return host, int(port)

    def _write_proxychains(self, socks_type, host, port):
        conf = self._proxychains_conf()
        conf.parent.mkdir(parents=True, exist_ok=True)
        conf.write_text(
            "# Managed by VoidWalker (voidwalker proxy) — edit or delete freely.\n"
            "# proxychains4 reads this before /etc/proxychains4.conf.\n"
            "dynamic_chain\n"
            "proxy_dns\n"
            "remote_dns_subnet 224\n"
            "tcp_read_time_out 15000\n"
            "tcp_connect_time_out 8000\n"
            "[ProxyList]\n"
            f"{socks_type} {host} {port}\n"
        )
        return conf

    def _print_proxy_usage(self, host, port):
        print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} SOCKS proxy set: "
              f"{Colors.WHITE}{host}:{port}{Colors.RESET} "
              f"{Colors.GRAY}→ {self._proxychains_conf()}{Colors.RESET}")
        if not shutil.which("proxychains4"):
            print(f"  {Colors.YELLOW}{Symbols.CIRCLE} proxychains4 isn't installed — "
                  f"apt install proxychains4 (or run the arsenal's System Packages).{Colors.RESET}")
        print(f"  {Colors.NEON_CYAN}Usage:{Colors.RESET} "
              f"{Colors.WHITE}proxychains4 nmap -sT -Pn <target>{Colors.RESET}  ·  "
              f"{Colors.WHITE}proxychains4 nxc smb <target>{Colors.RESET}")
        print(f"  {Colors.GRAY}First open the tunnel, e.g.: ssh -D {port} user@pivot  "
              f"(or chisel / ligolo-ng).{Colors.RESET}")

    def _proxy_cheatsheet(self):
        c, w, g = Colors.NEON_CYAN, Colors.WHITE, Colors.GRAY
        print(f"  {c}SSH dynamic SOCKS:{Colors.RESET}  {w}ssh -D {_DEFAULT_PORT} user@pivot{Colors.RESET} "
              f"{g}(then proxychains4 <tool>){Colors.RESET}")
        print(f"  {c}chisel (reverse SOCKS):{Colors.RESET}")
        print(f"     {w}attacker:{Colors.RESET} {g}chisel server -p 8080 --reverse{Colors.RESET}")
        print(f"     {w}target:  {Colors.RESET} {g}chisel client <attacker>:8080 R:{_DEFAULT_PORT}:socks{Colors.RESET}")
        print(f"  {c}ligolo-ng:{Colors.RESET}")
        print(f"     {w}attacker:{Colors.RESET} {g}ligolo-proxy -selfcert{Colors.RESET}  "
              f"{g}(add a route to the internal subnet, then start the tunnel){Colors.RESET}")
        print(f"     {w}target:  {Colors.RESET} {g}agent -connect <attacker>:11601 -ignore-cert{Colors.RESET}")
        print(f"  {g}ligolo-ng gives a real tun interface (no proxychains needed); "
              f"chisel/ssh -D need proxychains4.{Colors.RESET}")

    # ── entry points ───────────────────────────────────────────────────────
    def run_proxy(self, passthrough=None):
        """CLI entry: ``voidwalker proxy [host:port]``."""
        if passthrough:
            host, port = self._parse_socks(passthrough[0])
            if port is None:
                print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} invalid proxy "
                      f"'{passthrough[0]}' — use host:port or a port (e.g. 127.0.0.1:1080).{Colors.RESET}")
                return 1
            self._write_proxychains("socks5", host, port)
            self._print_proxy_usage(host, port)
            return 0
        return self.proxy_menu()

    def proxy_menu(self):
        while True:
            self.clear_screen()
            self.show_ascii_banner()
            print()
            self.print_centered(
                f"{Colors.NEON_MAGENTA}{Symbols.SHIELD} PROXY / PIVOT HELPER "
                f"{Colors.GRAY}(proxychains4){Colors.RESET}")
            self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
            print()

            content = []
            for i, (label, _) in enumerate(_PROXY_ACTIONS, 1):
                if label.startswith("Back"):
                    content.append(f"{Colors.BRIGHT_RED}[{i}] {label}{Colors.RESET}")
                else:
                    content.append(f"{Colors.NEON_CYAN}[{i}] {Colors.WHITE}{label}{Colors.RESET}")
            self.draw_box(f"{Symbols.GEAR} PROXY / PIVOT", content, 64)
            print()

            prompt = (f"{Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} "
                      f"Select option {Colors.GRAY}[1-{len(_PROXY_ACTIONS)}]{Colors.RESET}: ")
            try:
                choice = input(prompt).strip()
            except EOFError:
                return
            if not choice.isdigit() or not (1 <= int(choice) <= len(_PROXY_ACTIONS)):
                continue

            label, action = _PROXY_ACTIONS[int(choice) - 1]
            if action == "__back__":
                return

            print()
            if action == "__set__":
                try:
                    spec = input(f"  {Colors.NEON_CYAN}SOCKS proxy host:port "
                                 f"{Colors.GRAY}[{_DEFAULT_HOST}:{_DEFAULT_PORT}]{Colors.RESET}: ").strip()
                except EOFError:
                    spec = ""
                spec = spec or f"{_DEFAULT_HOST}:{_DEFAULT_PORT}"
                host, port = self._parse_socks(spec)
                if port is None:
                    print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} invalid host:port.{Colors.RESET}")
                else:
                    self._write_proxychains("socks5", host, port)
                    self._print_proxy_usage(host, port)
            elif action == "__show__":
                conf = self._proxychains_conf()
                if conf.exists():
                    print(f"  {Colors.GRAY}{conf}:{Colors.RESET}\n{conf.read_text()}")
                else:
                    print(f"  {Colors.YELLOW}No managed config yet — choose 'Set SOCKS proxy'.{Colors.RESET}")
            elif action == "__cheat__":
                self._proxy_cheatsheet()

            print()
            input(f"{Colors.GRAY}Press Enter to return to the proxy menu...{Colors.RESET}")
