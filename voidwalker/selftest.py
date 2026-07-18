"""Offline catalog validation — `voidwalker selftest`.

Checks the data catalog for internal consistency without touching the network:
well-formed ``(os, arch)`` keys and URLs, per-arch asset coverage, duplicate
package entries, and category shape. Exits non-zero if any *error* is found
(warnings are informational and do not fail the run).
"""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from .theme import Colors, Symbols
from .hostinfo import HostInfo, select_asset, OS_LINUX, OS_DARWIN, OS_WINDOWS
from .data.binaries import CROSS_PLATFORM_TOOLS, SPECIAL_TOOLS
from .data.catalog import TOOL_CATEGORIES
from .data import packages as pkg
from .integrations import assets_present, PENTEST_ENV_GUIDE, PENTEST_ENV_GUIDE_PAGES

_VALID_OS = {OS_LINUX, OS_DARWIN, OS_WINDOWS}
_VALID_ARCH = {"amd64", "arm64", "armv7", "386"}
_SUPPORTED_HOSTS = [
    HostInfo(OS_LINUX, "amd64"), HostInfo(OS_LINUX, "arm64"), HostInfo(OS_LINUX, "armv7"),
    HostInfo(OS_DARWIN, "amd64"), HostInfo(OS_DARWIN, "arm64"),
]


class _GuideParser(HTMLParser):
    """Collect local assets and IDs from one handbook page."""

    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        link = values.get("href") if tag in ("a", "link") else values.get("src")
        if link:
            self.links.append(link)


def _check_html_guide(errors):
    """Validate the offline guide bundle, including the CSS regression path."""
    page_ids = {}
    page_links = {}

    for name in PENTEST_ENV_GUIDE_PAGES:
        page = PENTEST_ENV_GUIDE / name
        if not page.is_file():
            errors.append(f"HTML guide page missing: {name}")
            continue
        parser = _GuideParser()
        try:
            parser.feed(page.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            errors.append(f"HTML guide unreadable: {name}: {exc}")
            continue
        duplicate_ids = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
        if duplicate_ids:
            errors.append(f"HTML guide {name}: duplicate IDs {duplicate_ids}")
        if "content" not in parser.ids:
            errors.append(f"HTML guide {name}: missing #content landmark")
        page_ids[page.resolve()] = set(parser.ids)
        page_links[page.resolve()] = parser.links

    guide_root = PENTEST_ENV_GUIDE.resolve()
    for page, links in page_links.items():
        for link in links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            target = page if not parsed.path else (page.parent / unquote(parsed.path)).resolve()
            try:
                target.relative_to(guide_root)
            except ValueError:
                errors.append(f"HTML guide {page.name}: link escapes guide bundle: {link}")
                continue
            if not target.is_file():
                errors.append(f"HTML guide {page.name}: missing local asset/link: {link}")
                continue
            if parsed.fragment and target.suffix.lower() == ".html":
                fragment = unquote(parsed.fragment)
                if fragment not in page_ids.get(target, set()):
                    errors.append(
                        f"HTML guide {page.name}: missing fragment #{fragment} in {target.name}"
                    )


def _check_assets(label, assets, errors, warnings):
    if not isinstance(assets, dict) or not assets:
        errors.append(f"{label}: missing/empty 'assets'")
        return
    for key, binaries in assets.items():
        if not (isinstance(key, tuple) and len(key) == 2):
            errors.append(f"{label}: asset key {key!r} is not an (os, arch) tuple")
            continue
        os_name, arch = key
        if os_name not in _VALID_OS:
            errors.append(f"{label}: invalid OS '{os_name}' in key {key}")
        if arch not in _VALID_ARCH:
            errors.append(f"{label}: invalid arch '{arch}' in key {key}")
        if not isinstance(binaries, list) or not binaries:
            errors.append(f"{label}: assets[{key}] must be a non-empty list")
            continue
        for entry in binaries:
            if not (isinstance(entry, tuple) and len(entry) == 2):
                errors.append(f"{label}: malformed asset entry {entry!r} for {key}")
                continue
            fname, url = entry
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                errors.append(f"{label}: bad URL for {fname!r}: {url!r}")


def run_selftest() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Cross-platform binaries.
    for name, cfg in CROSS_PLATFORM_TOOLS.items():
        if "description" not in cfg:
            warnings.append(f"CROSS_PLATFORM_TOOLS[{name}]: no description")
        if not any(k in cfg for k in ("dest_dir", "dest_dir_win", "dest_dir_linux", "dest_dir_darwin")):
            errors.append(f"CROSS_PLATFORM_TOOLS[{name}]: no dest_dir")
        _check_assets(f"CROSS_PLATFORM_TOOLS[{name}]", cfg.get("assets", {}), errors, warnings)

    # 2. Host-native binaries.
    for name, cfg in SPECIAL_TOOLS.items():
        if "dest" not in cfg:
            errors.append(f"SPECIAL_TOOLS[{name}]: no 'dest'")
        _check_assets(f"SPECIAL_TOOLS[{name}]", cfg.get("assets", {}), errors, warnings)

    # 3. Per-arch resolution: every supported host must resolve transfer + host tools cleanly.
    coverage = {}
    for host in _SUPPORTED_HOSTS:
        resolved = 0
        for cfg in CROSS_PLATFORM_TOOLS.values():
            if cfg.get("transfer"):
                resolved += 1  # transfer tools are always (partially) covered
            elif select_asset(cfg.get("assets", {}), host):
                resolved += 1
        coverage[host.label()] = resolved

    # 4. Package lists: non-empty + duplicate detection.
    for list_name in ("APT_TOOLS", "BREW_TOOLS", "BREW_CASKS", "PIPX_TOOLS",
                      "GO_TOOLS", "CARGO_TOOLS", "GEM_TOOLS", "UV_TOOLS"):
        items = getattr(pkg, list_name)
        if not items:
            warnings.append(f"{list_name} is empty")
        # GO_TOOLS entries are (name, cmd) tuples; others are strings.
        keys = [i[0] if isinstance(i, tuple) else i for i in items]
        dupes = {k for k in keys if keys.count(k) > 1}
        if dupes:
            warnings.append(f"{list_name}: duplicate entries {sorted(dupes)}")

    # 5. Categories: shape + no vestigial 'function' key.
    for cat, data in TOOL_CATEGORIES.items():
        if "function" in data:
            errors.append(f"TOOL_CATEGORIES[{cat}]: stale 'function' key remains")
        if not any(k in data for k in ("tools", "files", "repos", "special")):
            errors.append(f"TOOL_CATEGORIES[{cat}]: no installable items")

    # 6. Vendored integrations (pimpmykali + pentest-env): assets must ship.
    integ = assets_present()
    for name, present in integ.items():
        if not present:
            errors.append(f"integration asset missing: {name}")
    _check_html_guide(errors)

    # 7. BloodHound-CE: the bloodhound-cli download must resolve for the attack
    #    hosts upstream actually ships (linux/darwin amd64+arm64 — no 32-bit arm).
    #    It's fetched on demand, so this is a resolvability check, not a shipped asset.
    from .integrations.bloodhound import bh_asset_for
    _BH_HOSTS = [
        HostInfo(OS_LINUX, "amd64"), HostInfo(OS_LINUX, "arm64"),
        HostInfo(OS_DARWIN, "amd64"), HostInfo(OS_DARWIN, "arm64"),
    ]
    for host in _BH_HOSTS:
        if not bh_asset_for(host):
            errors.append(f"bloodhound-cli: no asset resolves for {host.label()}")

    # ── report ───────────────────────────────────────────────────────────────
    c = Colors
    print(f"\n{c.NEON_MAGENTA}{Symbols.SHIELD} VoidWalker catalog self-test{c.RESET}")
    print(f"{c.GRAY}{'─' * 60}{c.RESET}")
    print(f"  cross-platform tools : {len(CROSS_PLATFORM_TOOLS)}")
    print(f"  host-native tools    : {len(SPECIAL_TOOLS)}")
    print(f"  tool categories      : {len(TOOL_CATEGORIES)}")
    print(f"  integrations         : pimpmykali + pentest-env + bloodhound-ce "
          f"({sum(integ.values())}/{len(integ)} vendored assets present)")
    print(f"  per-host resolution  :")
    for label, n in coverage.items():
        print(f"      {c.NEON_GREEN}{label:<14}{c.RESET} {n} tool(s) resolve")

    for w in warnings:
        print(f"  {c.YELLOW}{Symbols.ARROW_RIGHT} warn:{c.RESET} {w}")
    for e in errors:
        print(f"  {c.BRIGHT_RED}{Symbols.CROSS} error:{c.RESET} {e}")

    if errors:
        print(f"\n{c.BRIGHT_RED}{Symbols.CROSS} self-test FAILED with {len(errors)} error(s).{c.RESET}\n")
        return 1
    print(f"\n{c.NEON_GREEN}{Symbols.CHECK} self-test passed "
          f"({len(warnings)} warning(s)).{c.RESET}\n")
    return 0
