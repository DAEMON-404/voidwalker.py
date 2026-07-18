"""Engagement logging + evidence capture.

Pentest reports need an audit trail: what was run, when, and screenshots of the
result. This records a shell session (asciinema if present, else util-linux
``script``) and grabs screenshots into a per-engagement workspace under
``~/voidwalker/engagements/<name>/`` (``logs/`` + ``evidence/``).

Entry points:
* ``voidwalker rec``                — interactive submenu
* ``voidwalker rec shell [name]``   — start a recorded shell
* ``voidwalker rec shot  [name]``   — capture a screenshot
* ``voidwalker rec <name>``         — recorded shell for that engagement
* main-menu *Engagement logging / evidence*

No new heavy dependencies — uses asciinema/script and any of
flameshot/maim/scrot/import (Linux) or the built-in screencapture (macOS).
"""

from __future__ import annotations

import shutil
import subprocess
import time

from ..theme import Colors, Symbols

_REC_ACTIONS = [
    ("Start a recorded shell (asciinema / script)", "__shell__"),
    ("Capture a screenshot into evidence/", "__shot__"),
    ("Show engagement workspace", "__show__"),
    ("Back to main menu", "__back__"),
]


def _safe(name):
    keep = "-_. "
    cleaned = "".join(c for c in name if c.isalnum() or c in keep).strip().replace(" ", "_")
    return cleaned or "default"


class RecorderMixin:
    """Mixed into :class:`~voidwalker.core.VoidWalker`."""

    def _eng_dir(self, name):
        return self.base_path / "engagements" / _safe(name)

    def _ask_engagement(self, name=None):
        if name:
            return _safe(name)
        try:
            raw = input(f"  {Colors.NEON_CYAN}Engagement name {Colors.GRAY}[default]{Colors.RESET}: ").strip()
        except EOFError:
            raw = ""
        return _safe(raw or "default")

    def _start_recording(self, name):
        ws = self._eng_dir(name)
        logs = ws / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        if shutil.which("asciinema"):
            out = logs / f"session-{ts}.cast"
            tool = ["asciinema", "rec", str(out)]
        elif shutil.which("script"):
            out = logs / f"session-{ts}.log"
            tool = ["script", "-q", str(out)]
        else:
            print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} need 'asciinema' or 'script' "
                  f"(util-linux) to record. Install one and retry.{Colors.RESET}")
            return
        print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} recording to {Colors.WHITE}{out}{Colors.RESET}")
        print(f"  {Colors.GRAY}A logged sub-shell starts now — type 'exit' to stop recording.{Colors.RESET}\n")
        try:
            subprocess.run(tool)
        except (FileNotFoundError, KeyboardInterrupt):
            pass
        print(f"\n  {Colors.NEON_GREEN}{Symbols.CHECK} saved: {out}{Colors.RESET}")
        self.log(f"engagement '{name}' recording saved: {out}")

    def _screenshot(self, name):
        ws = self._eng_dir(name)
        ev = ws / "evidence"
        ev.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        out = ev / f"shot-{ts}.png"
        # (tool, argv) — prefer interactive region selectors, fall back to full-screen.
        if self.is_macos:
            candidates = [("screencapture", ["-i", str(out)])]
        else:
            candidates = [
                ("flameshot", ["gui", "-p", str(ev)]),  # interactive; saves into ev/
                ("maim", ["-s", str(out)]),             # interactive region
                ("scrot", ["-s", str(out)]),            # interactive region
                ("import", [str(out)]),                 # ImageMagick: click/drag
            ]
        for tool, args in candidates:
            if shutil.which(tool):
                print(f"  {Colors.YELLOW}{tool}: select a region…{Colors.RESET}")
                self.run_cmd([tool, *args], timeout=120)
                # flameshot saves its own filename into ev/; others write `out`.
                saved = out if out.exists() else ev
                print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} evidence in {Colors.WHITE}{saved}{Colors.RESET}")
                self.log(f"engagement '{name}' screenshot via {tool} -> {ev}")
                return
        tools = "flameshot/maim/scrot/imagemagick" if not self.is_macos else "screencapture"
        print(f"  {Colors.BRIGHT_RED}{Symbols.CROSS} no screenshot tool found ({tools}).{Colors.RESET}")

    def _show_workspace(self, name):
        ws = self._eng_dir(name)
        print(f"  {Colors.ELECTRIC_BLUE}Workspace:{Colors.RESET} {Colors.WHITE}{ws}{Colors.RESET}")
        if not ws.exists():
            print(f"  {Colors.GRAY}(nothing recorded yet){Colors.RESET}")
            return
        for sub in ("logs", "evidence"):
            d = ws / sub
            files = sorted(d.glob("*")) if d.exists() else []
            print(f"  {Colors.NEON_CYAN}{sub}/{Colors.RESET} {Colors.GRAY}({len(files)} file(s)){Colors.RESET}")
            for f in files[-8:]:
                print(f"     {Colors.GRAY}{f.name}{Colors.RESET}")

    # ── entry points ───────────────────────────────────────────────────────
    def run_rec(self, passthrough=None):
        """CLI entry: ``voidwalker rec [shell|shot] [name]`` or ``rec <name>``."""
        passthrough = list(passthrough or [])
        if not passthrough:
            return self.run_recorder_menu()
        verb = passthrough[0].lower()
        if verb in ("shell", "rec", "record"):
            self._start_recording(self._ask_engagement(passthrough[1] if len(passthrough) > 1 else None))
        elif verb in ("shot", "screenshot", "screen"):
            self._screenshot(self._ask_engagement(passthrough[1] if len(passthrough) > 1 else None))
        else:
            # treat the first token as an engagement name → recorded shell
            self._start_recording(self._ask_engagement(passthrough[0]))
        return 0

    def run_recorder_menu(self):
        while True:
            self.clear_screen()
            self.show_ascii_banner()
            print()
            self.print_centered(
                f"{Colors.NEON_MAGENTA}{Symbols.SHIELD} ENGAGEMENT LOGGING / EVIDENCE{Colors.RESET}")
            self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
            print()

            content = []
            for i, (label, _) in enumerate(_REC_ACTIONS, 1):
                if label.startswith("Back"):
                    content.append(f"{Colors.BRIGHT_RED}[{i}] {label}{Colors.RESET}")
                else:
                    content.append(f"{Colors.NEON_CYAN}[{i}] {Colors.WHITE}{label}{Colors.RESET}")
            self.draw_box(f"{Symbols.GEAR} ENGAGEMENT LOG", content, 60)
            print()

            prompt = (f"{Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} "
                      f"Select option {Colors.GRAY}[1-{len(_REC_ACTIONS)}]{Colors.RESET}: ")
            try:
                choice = input(prompt).strip()
            except EOFError:
                return
            if not choice.isdigit() or not (1 <= int(choice) <= len(_REC_ACTIONS)):
                continue

            label, action = _REC_ACTIONS[int(choice) - 1]
            if action == "__back__":
                return

            print()
            if action == "__shell__":
                self._start_recording(self._ask_engagement())
            elif action == "__shot__":
                self._screenshot(self._ask_engagement())
            elif action == "__show__":
                self._show_workspace(self._ask_engagement())

            print()
            input(f"{Colors.GRAY}Press Enter to return to the logging menu...{Colors.RESET}")
