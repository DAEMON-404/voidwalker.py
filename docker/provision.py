#!/usr/bin/env python3
"""Container provisioning driver for the Kali HTB image.

This is the bridge between the Docker build and VoidWalker. Rather than
re-listing tools (which would drift from the project), it imports VoidWalker's
own catalog and *reuses* its arch-aware binary downloader — but drives package
installs non-interactively, as root, batched, and trimmed for a headless
container (VoidWalker's own installers assume an interactive host, `sudo`, and a
one-package-at-a-time TUI).

Stages (selected via argv):
    --print-apt      print the trimmed APT_TOOLS list (consumed by the Dockerfile)
    --stage lang     pipx / uv / go / gem tools
    --stage binaries arch-aware droppable binaries + workspace + symlinks
    --all            lang + binaries (default)

Everything is best-effort: a single tool that fails to build/download must not
abort the image build, so failures are logged and skipped.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# VoidWalker is pip-installed into the image before this runs.
from voidwalker.data.packages import (
    APT_TOOLS, PIPX_TOOLS, GO_TOOLS, GEM_TOOLS, UV_TOOLS,
)
from voidwalker.data.binaries import SPECIAL_TOOLS
from voidwalker.data.workspace import WORKSPACE_DIRS
from voidwalker.hostinfo import HostInfo

HOME = Path(os.environ.get("HOME", "/root"))
HOST = HostInfo.current()            # linux/arm64 or linux/amd64 inside the image
ARCH = HOST.arch                     # "arm64" | "amd64"

# ── Lean container profile ───────────────────────────────────────────────────
# GUI apps and wireless tooling are useless in a headless container with no
# display and no radio; ghidra/autopsy are huge Java GUIs. Drop them; keep the
# CLI equivalents (tshark/tcpdump stay, wireshark GUI goes).
CONTAINER_SKIP_APT = {
    "wireshark", "ghidra", "autopsy", "dirbuster", "veil",
    "aircrack-ng", "reaver", "bully", "pixiewps", "wifite", "kismet",
    "mdk3", "mdk4", "macchanger", "iw", "wireless-tools",
    # provided more reliably elsewhere / already base deps:
    "tmux", "vim", "nano", "git", "curl", "wget",
}

# pipx is slow (one venv per tool). Keep the HTB-essential subset; the rest stay
# reachable at runtime via `pipx install X` or `voidwalker`. Big AD tools
# (impacket/netexec/certipy/bloodyad) come from UV_TOOLS, not pipx.
PIPX_KEEP = {
    "bloodhound-python", "bloodhound-ce-python", "ldapdomaindump", "mitm6",
    "coercer", "pypykatz", "adidnsdump", "pre2k", "sprayhound", "donpapi",
    "dploot", "lsassy", "certsync", "theHarvester", "dirsearch", "arjun",
    "pwntools", "ropgadget", "ropper", "name-that-hash", "updog",
    "pwncat-cs", "villain", "hoaxshell", "oletools",
}


def log(msg: str) -> None:
    print(f"[provision] {msg}", flush=True)


def run(cmd, timeout: int = 1800) -> bool:
    """Run a command, stream output, never raise. Returns success."""
    if isinstance(cmd, str):
        shown, kw = cmd, {"shell": True}
    else:
        shown, kw = " ".join(cmd), {}
    try:
        return subprocess.run(cmd, timeout=timeout, **kw).returncode == 0
    except Exception as exc:  # noqa: BLE001 - build must not die on one tool
        log(f"! failed: {shown} :: {exc}")
        return False


# ── apt list (printed for the Dockerfile) ────────────────────────────────────
def apt_list() -> list[str]:
    seen, out = set(), []
    for pkg in APT_TOOLS:
        if pkg in CONTAINER_SKIP_APT or pkg in seen:
            continue
        seen.add(pkg)
        out.append(pkg)
    return out


# ── language / package-manager tools ─────────────────────────────────────────
def stage_lang() -> None:
    log("pipx tools (curated HTB subset)")
    run(["pipx", "ensurepath"])
    for tool in PIPX_TOOLS:
        if tool in PIPX_KEEP:
            run(["pipx", "install", tool], timeout=900)

    log("uv + uv-managed tools (impacket/netexec/certipy/bloodyad/bofhound)")
    if not run(["uv", "--version"]):
        run([sys.executable, "-m", "pip", "install", "--break-system-packages", "uv"])
    for tool in UV_TOOLS:
        run(["uv", "tool", "install", tool], timeout=900)

    log("go tools (ffuf, nuclei, httpx, katana, …)")
    env_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{HOME}/go/bin:{env_path}"
    for name, cmd in GO_TOOLS:
        if cmd.startswith("go install"):
            run(cmd.split(), timeout=1200)

    log("ruby gems (wpscan, evil-winrm)")
    for gem in GEM_TOOLS:
        run(["gem", "install", "--no-document", gem], timeout=900)


# ── arch-aware droppable binaries (reuse VoidWalker's downloader) ────────────
def _symlink_first(glob_pat: str, link_name: str) -> None:
    """Symlink the first match of a glob under ~/voidwalker into /usr/local/bin."""
    matches = sorted((HOME / "voidwalker").glob(glob_pat))
    if not matches:
        log(f"~ no match for {glob_pat} (skipping {link_name} symlink)")
        return
    target = matches[0]
    link = Path("/usr/local/bin") / link_name
    try:
        target.chmod(0o755)
        link.unlink(missing_ok=True)
        link.symlink_to(target)
        log(f"+ {link_name} -> {target}")
    except Exception as exc:  # noqa: BLE001
        log(f"! symlink {link_name} failed: {exc}")


def stage_binaries() -> None:
    log("workspace scaffold (~/voidwalker + engagement template)")
    base = HOME / "voidwalker"
    for d in WORKSPACE_DIRS:
        (base / d).mkdir(parents=True, exist_ok=True)

    log("arch-aware binaries via VoidWalker (all transfer variants + host-native)")
    from voidwalker.core import VoidWalker
    vw = VoidWalker()
    vw.install_cross_platform_tools()
    for name, cfg in SPECIAL_TOOLS.items():
        vw.install_special_tool(name, cfg)

    log(f"convenience symlinks for host arch ({HOST.label()})")
    pspy = "pspy64arm" if ARCH == "arm64" else "pspy64"
    _symlink_first(f"tools/linux/privesc/linux/{ARCH}/linpeas.sh", "linpeas")
    _symlink_first(f"tools/linux/enum/linux/{ARCH}/{pspy}", "pspy")
    _symlink_first(f"tools/pivoting/chisel/linux/{ARCH}/chisel*", "chisel")
    _symlink_first(f"tools/pivoting/ligolo-ng/linux/{ARCH}/proxy", "ligolo-proxy")
    _symlink_first(f"tools/pivoting/ligolo-ng/linux/{ARCH}/agent", "ligolo-agent")
    _symlink_first(f"tools/pivoting/netcat/linux/{ARCH}/ncat*", "ncat-static")


def main() -> int:
    argv = sys.argv[1:]
    if "--print-apt" in argv:
        print(" ".join(apt_list()))
        return 0

    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "all"
    do_all = "--all" in argv or stage == "all"

    if do_all or stage == "lang":
        stage_lang()
    if do_all or stage == "binaries":
        stage_binaries()

    log("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
