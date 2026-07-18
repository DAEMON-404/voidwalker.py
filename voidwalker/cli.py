"""Command-line entry point and sub-command dispatch.

Preserves the original commands (``poc``/``nse``/``shodan``/``exploitdb``/``dork``
and the bare interactive installer) and adds:

* ``--theme NAME``  — switch the colour palette (also ``VOIDWALKER_THEME`` env);
* ``--dry-run``     — print the detected host and exactly what *would* be
  installed for this architecture, without downloading anything;
* ``selftest``      — offline validation of the catalog (see :mod:`.selftest`).

Integrations folded into VoidWalker (see :mod:`.integrations`):

* ``kali  [flags]`` — the *pimpmykali* Kali fix/harden engine (passthrough);
* ``env   [flags]`` — deploy the *pentest-env* ``pe`` toolkit (``install.sh``);
* ``pe    <args>``  — passthrough to the encrypted ``pe`` workspace manager;
* ``pt    [flags]`` — install Parallels Tools in a Kali guest (``pt-install``);
* ``bloodhound``    — install + configure BloodHound-CE via ``bloodhound-cli``;
* ``proxy [h:p]``   — wire proxychains4 to a SOCKS pivot;
* ``rec [shell|shot]`` — record a shell / capture screenshots for the engagement log.

Global options (``--theme``/``--dry-run``/``-v``) must precede the command so the
remaining tokens can be passed verbatim to the integration that owns them.
"""

from __future__ import annotations

import argparse
import os
import sys

from .version import __version__
from .theme import Colors, Symbols, apply_theme, list_themes
from .hostinfo import HostInfo
from .search import (
    search_poc, search_nse, search_exploitdb, search_shodan, dork_generator,
)


def _err(msg: str, example: str) -> None:
    print(f"{Colors.BRIGHT_RED}Error: {msg}{Colors.RESET}")
    print(f"{Colors.GRAY}Example: {example}{Colors.RESET}")
    sys.exit(1)


def _dry_run(host: HostInfo) -> None:
    """Print the install plan for the detected architecture (no downloads)."""
    from .data.binaries import CROSS_PLATFORM_TOOLS, SPECIAL_TOOLS
    from .data.packages import (
        APT_TOOLS, BREW_TOOLS, PIPX_TOOLS, UV_TOOLS, GO_TOOLS, CARGO_TOOLS, GEM_TOOLS,
    )
    from .hostinfo import select_asset

    c = Colors
    print(f"\n{c.NEON_MAGENTA}{Symbols.ROCKET} VoidWalker dry-run — nothing will be downloaded{c.RESET}")
    print(f"{c.GRAY}{'─' * 60}{c.RESET}")
    print(f"  {c.WHITE}Detected host:{c.RESET} {c.NEON_GREEN}{host.label()}{c.RESET} "
          f"{c.GRAY}(deb arch: {host.deb_arch}){c.RESET}\n")

    pkg_mgr = "brew" if host.is_macos else "apt"
    sys_list = BREW_TOOLS if host.is_macos else APT_TOOLS
    print(f"  {c.ELECTRIC_BLUE}System packages ({pkg_mgr}):{c.RESET} {len(sys_list)}")
    print(f"  {c.ELECTRIC_BLUE}pipx tools:{c.RESET} {len(PIPX_TOOLS)}    "
          f"{c.ELECTRIC_BLUE}uv tools:{c.RESET} {len(UV_TOOLS)}    "
          f"{c.ELECTRIC_BLUE}go tools:{c.RESET} {len(GO_TOOLS)}    "
          f"{c.ELECTRIC_BLUE}cargo:{c.RESET} {len(CARGO_TOOLS)}    "
          f"{c.ELECTRIC_BLUE}gems:{c.RESET} {len(GEM_TOOLS)}\n")

    print(f"  {c.NEON_CYAN}Cross-platform binaries:{c.RESET}")
    fetch = skip = 0
    for name, cfg in CROSS_PLATFORM_TOOLS.items():
        assets = cfg.get("assets", {})
        if cfg.get("transfer"):
            variants = sum(len(v) for v in assets.values())
            archset = sorted({a for (_, a) in assets})
            print(f"    {c.NEON_GREEN}{Symbols.CHECK}{c.RESET} {name:<22} "
                  f"{c.GRAY}all {variants} variant(s): {', '.join(archset)}{c.RESET}")
            fetch += variants
        else:
            picked = select_asset(assets, host)
            if picked:
                print(f"    {c.NEON_GREEN}{Symbols.CHECK}{c.RESET} {name:<22} "
                      f"{c.GRAY}host build ({host.label()}){c.RESET}")
                fetch += len(picked)
            else:
                print(f"    {c.BRIGHT_RED}{Symbols.CROSS}{c.RESET} {name:<22} "
                      f"{c.GRAY}no build for {host.label()} — skipped{c.RESET}")
                skip += 1

    print(f"\n  {c.NEON_CYAN}Host-native PATH binaries:{c.RESET}")
    for name, cfg in SPECIAL_TOOLS.items():
        picked = select_asset(cfg.get("assets", {}), host)
        mark = (f"{c.NEON_GREEN}{Symbols.CHECK}" if picked else f"{c.BRIGHT_RED}{Symbols.CROSS}")
        detail = host.label() if picked else f"no build for {host.label()}"
        print(f"    {mark}{c.RESET} {name:<22} {c.GRAY}{detail}{c.RESET}")

    print(f"\n  {c.YELLOW}Plan: ~{fetch} binary download(s), {skip} tool(s) skipped for this arch.{c.RESET}\n")


# Commands that pass their remaining tokens verbatim to a vendored integration.
_SEARCH_COMMANDS = {"poc", "nse", "shodan", "exploitdb", "dork"}
_INTEGRATION_COMMANDS = {"kali", "pimp", "harden", "env", "setup-env", "pe",
                         "pt", "pt-install", "parallels-tools",
                         "bloodhound", "bh", "bhce",
                         "proxy", "rec", "record",
                         "root", "rootsetup"}
_KNOWN_COMMANDS = _SEARCH_COMMANDS | _INTEGRATION_COMMANDS | {"selftest"}


def _dispatch_integration(command: str, rest: list) -> None:
    """Construct VoidWalker and route an integration sub-command, then exit."""
    from .core import VoidWalker
    vw = VoidWalker()
    if command in ("kali", "pimp", "harden"):
        rc = vw.run_kali_fix(rest)
    elif command in ("env", "setup-env"):
        rc = vw.deploy_pentest_env(rest)
    elif command == "pe":
        rc = vw.run_pe(rest)
    elif command in ("pt", "pt-install", "parallels-tools"):
        rc = vw.run_parallels_tools(rest)
    elif command in ("bloodhound", "bh", "bhce"):
        rc = vw.run_bloodhound(rest)
    elif command == "proxy":
        rc = vw.run_proxy(rest)
    elif command in ("rec", "record"):
        rc = vw.run_rec(rest)
    elif command in ("root", "rootsetup"):
        rc = vw.run_root_setup(rest)
    else:  # unreachable
        rc = 2
    sys.exit(rc or 0)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="voidwalker",
        description=f"{Colors.NEON_CYAN}VoidWalker v{__version__}{Colors.RESET} - Elite Penetration Testing Arsenal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{Colors.NEON_GREEN}Commands:{Colors.RESET}
  {Colors.WHITE}poc <CVE-ID>{Colors.RESET}       Search for PoC exploits (e.g., poc CVE-2021-1675)
  {Colors.WHITE}nse <keyword>{Colors.RESET}      Search Nmap NSE scripts (e.g., nse http, nse smb)
  {Colors.WHITE}shodan <query>{Colors.RESET}     Search Shodan (requires SHODAN_API_KEY env var)
  {Colors.WHITE}exploitdb <query>{Colors.RESET}  Search Exploit-DB
  {Colors.WHITE}dork{Colors.RESET}               Interactive Google Dork generator
  {Colors.WHITE}selftest{Colors.RESET}           Validate the tool catalog + integrations (offline)
  {Colors.WHITE}kali [flags]{Colors.RESET}       Fix / harden Kali via the pimpmykali engine
  {Colors.WHITE}env  [flags]{Colors.RESET}       Deploy the pentest-env (pe) toolkit
  {Colors.WHITE}pe   <args>{Colors.RESET}        Encrypted pe workspace (flags/creds/hosts/notes)
  {Colors.WHITE}pt   [flags]{Colors.RESET}       Install Parallels Tools in a Kali guest
  {Colors.WHITE}bloodhound{Colors.RESET}         Install + configure BloodHound-CE (bloodhound-cli)
  {Colors.WHITE}proxy [host:port]{Colors.RESET}  Wire proxychains4 to a SOCKS pivot (default 127.0.0.1:1080)
  {Colors.WHITE}rec [shell|shot]{Colors.RESET}   Record a shell / capture screenshots into the engagement log
  {Colors.WHITE}root [setup|link]{Colors.RESET}  Red root prompt + expose your user tools (netexec, ...) to root

{Colors.NEON_GREEN}Examples:{Colors.RESET}
  python3 voidwalker.py                      # Interactive installer menu
  python3 voidwalker.py --dry-run            # Show the per-arch install plan
  python3 voidwalker.py --theme matrix       # Switch colour palette
  python3 voidwalker.py poc CVE-2021-44228   # Search Log4Shell PoCs
  python3 voidwalker.py kali --newvm         # Fresh-Kali setup (pimpmykali)
  python3 voidwalker.py env --dry-run        # Preview the pe environment install
  python3 voidwalker.py pe target add Cap --ip 10.10.10.245
""",
    )
    parser.add_argument("command", nargs="?", help="Command to execute (see below)")
    parser.add_argument("rest", nargs=argparse.REMAINDER,
                        help="Arguments / query / passthrough flags for the command")
    parser.add_argument("--theme", choices=list_themes(),
                        help="Colour palette (default from $VOIDWALKER_THEME or 'voidwalker')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the per-architecture install plan and exit")
    parser.add_argument("-v", "--version", action="version", version=f"VoidWalker v{__version__}")

    args = parser.parse_args()

    if args.theme:
        apply_theme(args.theme)

    command = args.command
    rest = list(args.rest)
    query = rest[0] if rest else None

    if command is not None and command not in _KNOWN_COMMANDS:
        _err(f"unknown command: {command}",
             "python3 voidwalker.py kali --newvm  (or run with no command for the menu)")

    if command == "poc":
        if not query:
            _err("Please provide a CVE ID or keyword", "python3 voidwalker.py poc CVE-2021-1675")
        search_poc(query)
    elif command == "nse":
        if not query:
            _err("Please provide a search keyword", "python3 voidwalker.py nse http")
        search_nse(query)
    elif command == "shodan":
        if not query:
            _err("Please provide a search query", "python3 voidwalker.py shodan apache")
        search_shodan(query)
    elif command == "exploitdb":
        if not query:
            _err("Please provide a search query", "python3 voidwalker.py exploitdb wordpress")
        search_exploitdb(query)
    elif command == "dork":
        dork_generator()
    elif command == "selftest":
        from .selftest import run_selftest
        sys.exit(run_selftest())
    elif command in _INTEGRATION_COMMANDS:
        _dispatch_integration(command, rest)
    elif args.dry_run:
        _dry_run(HostInfo.current())
    else:
        host = HostInfo.current()
        if host.is_linux and hasattr(os, "geteuid") and os.geteuid() != 0:
            print(f"{Colors.YELLOW}Note: Some installations require sudo privileges.{Colors.RESET}")
            print(f"{Colors.GRAY}Run with 'sudo python3 voidwalker.py' for full functionality.{Colors.RESET}\n")
        elif host.is_macos:
            print(f"{Colors.NEON_CYAN}Detected macOS — using Homebrew for package management.{Colors.RESET}\n")
        print(f"{Colors.GRAY}Host architecture: {host.label()}{Colors.RESET}\n")

        from .core import VoidWalker
        installer = VoidWalker()
        installer.run()


if __name__ == "__main__":
    main()
