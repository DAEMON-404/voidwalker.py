"""First-class integrations folded into VoidWalker.

VoidWalker historically shipped only the Python arsenal builder.  Two sibling
projects are now part of the same toolkit and are driven through the very same
CLI / TUI:

* **pimpmykali** — the battle-tested Kali "fix a fresh VM" engine, surfaced as
  :class:`~voidwalker.integrations.kali.KaliFixMixin`
  (``voidwalker kali`` / main-menu *Fix / Harden Kali*).
* **pentest-env** — the encrypted, target-centric ``pe`` workspace plus the
  Rose Pine ZSH/tmux, GNOME/XFCE desktop profiles, optional BSPWM rice, and
  offline HTML field manual, surfaced as
  :class:`~voidwalker.integrations.penv.PentestEnvMixin`
  (``voidwalker env`` / ``voidwalker pe`` / main-menu *Deploy Pentest Env*).

Rather than rewrite thousands of lines of proven shell (which would be the
opposite of "make sure everything works"), the original engines are **vendored
inside this package** under :mod:`voidwalker.integrations` ``assets/`` and wrapped
in thin, themed Python so that *everything lives under VoidWalker now* — one
package, one entry point, one UI.  The wrappers locate the bundled assets,
stage the ones that need a writable working directory, and shell out to them.
"""

from __future__ import annotations

import shutil
from pathlib import Path

# Directory holding the vendored upstream payloads (ships as package data).
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

PIMPMYKALI_DIR = ASSETS_DIR / "pimpmykali"
PENTEST_ENV_DIR = ASSETS_DIR / "pentest-env"

# Canonical entry points inside the vendored payloads.
PIMPMYKALI_SCRIPT = PIMPMYKALI_DIR / "pimpmykali.sh"
PENTEST_ENV_INSTALLER = PENTEST_ENV_DIR / "install.sh"
PENTEST_ENV_PE = PENTEST_ENV_DIR / "config" / "bin" / "pe"
PENTEST_ENV_PT = PENTEST_ENV_DIR / "config" / "scripts" / "parallels-tools.sh"
PENTEST_ENV_GUIDE = PENTEST_ENV_DIR / "config" / "guide"

PENTEST_ENV_GUIDE_PAGES = (
    "index.html", "tmux.html", "pe.html", "htb-workflow.html",
    "zsh-terminal.html", "recon.html", "web.html", "ad-windows.html",
    "privesc.html", "transfer.html", "toolbox.html",
)


def asset(*parts: str) -> Path:
    """Absolute path to a vendored integration asset."""
    return ASSETS_DIR.joinpath(*parts)


def stage_pimpmykali(workdir: Path) -> Path:
    """Copy the pimpmykali engine into a writable *workdir* and return the script.

    pimpmykali writes its run log (``pimpmykali.log``) and assorted temp files
    into the *current directory*, and reads ``./addons/fixed-http-shellshock.nse``
    as the offline fallback for its nmap fix.  When VoidWalker is pip-installed
    its package directory may be read-only, so we mirror upstream's "clone & cd"
    model into a writable location the user owns before running.
    """
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "addons").mkdir(exist_ok=True)
    shutil.copy2(PIMPMYKALI_SCRIPT, workdir / "pimpmykali.sh")
    (workdir / "pimpmykali.sh").chmod(0o755)
    nse = PIMPMYKALI_DIR / "fixed-http-shellshock.nse"
    if nse.exists():
        shutil.copy2(nse, workdir / "fixed-http-shellshock.nse")
        shutil.copy2(nse, workdir / "addons" / "fixed-http-shellshock.nse")
    return workdir / "pimpmykali.sh"


def assets_present() -> dict:
    """Report which vendored entry points are present (used by ``selftest``)."""
    return {
        "pimpmykali.sh": PIMPMYKALI_SCRIPT.is_file(),
        "pentest-env/install.sh": PENTEST_ENV_INSTALLER.is_file(),
        "pentest-env/config/bin/pe": PENTEST_ENV_PE.is_file(),
        "pentest-env/config/bin/htb-session": (
            PENTEST_ENV_DIR / "config" / "bin" / "htb-session"
        ).is_file(),
        "pentest-env/scripts/parallels-tools.sh": PENTEST_ENV_PT.is_file(),
        "pentest-env/config/theme/install-gnome.sh": (
            PENTEST_ENV_DIR / "config" / "theme" / "install-gnome.sh"
        ).is_file(),
        "pentest-env/config/guide bundle": (
            all((PENTEST_ENV_GUIDE / page).is_file() for page in PENTEST_ENV_GUIDE_PAGES)
            and (PENTEST_ENV_GUIDE / "assets" / "style.css").is_file()
            and (PENTEST_ENV_GUIDE / "assets" / "app.js").is_file()
            and (PENTEST_ENV_DIR / "config" / "lib" / "guide.sh").is_file()
        ),
        "pimpmykali/addons/fixed-http-shellshock.nse": (
            PIMPMYKALI_DIR / "addons" / "fixed-http-shellshock.nse"
        ).is_file(),
    }
