"""Architecture-aware installation of standalone binaries.

Replaces the old OS-only logic with ``(os, arch)`` selection:

* **transfer** tools (``transfer: True``) are an arsenal you carry onto targets,
  so *every* published ``(os, arch)`` variant is fetched — including the ARM /
  aarch64 / armv7 and Windows-ARM64 builds added to the catalog.
* **host-native** tools are fetched only for the *current* host architecture via
  :func:`voidwalker.hostinfo.select_asset`, so an ARM attack box never ends up
  with an x86-only binary it cannot run.
"""

from __future__ import annotations

import gzip
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from .theme import Colors, Symbols
from .hostinfo import select_asset
from .data.binaries import CROSS_PLATFORM_TOOLS, SPECIAL_TOOLS


class CrossPlatformMixin:
    def _xplat_jobs(self, only: Optional[set] = None):
        """Flatten the catalog into a list of download jobs for this run.

        Each job: ``(tool_name, os, arch, filename, url, dest_dir)``.
        """
        jobs = []
        for tool_name, cfg in CROSS_PLATFORM_TOOLS.items():
            if only is not None and tool_name not in only:
                continue
            assets = cfg.get("assets", {})
            if cfg.get("transfer"):
                # Arsenal binary: grab every published (os, arch) variant.
                selected = list(assets.items())
            else:
                # Host-native: only the build matching this machine.
                picked = select_asset(assets, self.host)
                if not picked:
                    self.log(f"{tool_name}: no build for {self.host.label()} — skipped")
                    continue
                selected = [((self.host.os, self.host.arch), picked)]

            for (os_name, arch), binaries in selected:
                dest_key = (
                    cfg.get("dest_dir_win") if os_name == "windows" else
                    cfg.get("dest_dir_darwin") if os_name == "darwin" else
                    cfg.get("dest_dir_linux")
                ) or cfg.get("dest_dir", f"tools/pivoting/{tool_name}")
                dest_dir = self.base_path / dest_key / os_name / arch
                for filename, url in binaries:
                    jobs.append((tool_name, os_name, arch, filename, url, dest_dir))
        return jobs

    def install_cross_platform_tools(self, only: Optional[set] = None):
        """Download cross-platform binaries (all arches for transfer tools).

        ``only`` restricts the run to a set of tool names — used by
        :meth:`install_category` to honour a category's ``special`` key.
        """
        jobs = self._xplat_jobs(only)
        total_items = len(jobs)
        if total_items == 0:
            return

        xp_success, xp_fail = 0, 0
        for counter, (tool_name, os_name, arch, filename, url, dest_dir) in enumerate(jobs, 1):
            display_name = f"{tool_name}/{os_name}-{arch}/{filename}"
            self.show_live_status("Cross-Platform", counter, total_items, display_name[:30], "downloading")

            dest_file = dest_dir / filename
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            if url.endswith(".tar.gz"):
                success = self._download_and_extract_tar_gz(url, dest_dir, tool_name)
            elif url.endswith(".gz"):
                success = self._download_and_decompress_gz(url, dest_file)
            elif url.endswith(".zip"):
                success = self.download_and_extract_zip(url, dest_dir)
            else:
                success = self.download_file(url, dest_file)

            if success:
                if os_name in ("linux", "darwin") and dest_file.exists():
                    dest_file.chmod(0o755)
                xp_success += 1
                self.stats["ok"] += 1
            else:
                xp_fail += 1
                self.stats["fail"] += 1

        self.complete_status_line("Cross-Platform", xp_success, xp_fail)
        print()

    def install_special_tool(self, name: str, config: Dict) -> bool:
        """Install a single host-native binary onto PATH for the current arch."""
        try:
            picked = select_asset(config.get("assets", {}), self.host)
            if not picked:
                self.log(f"{name}: no host build for {self.host.label()} — skipped")
                return False

            dest_path = Path(config["dest"])
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            _, url = picked[0]

            if config.get("type", "binary") == "binary" and not url.endswith((".gz", ".tar.gz")):
                if self.download_file(url, dest_path):
                    if config.get("chmod"):
                        dest_path.chmod(0o755)
                    return True
                return False

            # Compressed single binary (.gz) or archive (.tar.gz).
            with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    tmp.write(resp.read())
                tmp_path = Path(tmp.name)

            if url.endswith(".tar.gz"):
                with tarfile.open(tmp_path, "r:gz") as tar:
                    target = name.split("-")[-1] if "-" in name else name
                    for member in tar.getmembers():
                        if member.isfile() and (member.name.endswith(target) or member.name == target):
                            member.name = dest_path.name
                            tar.extract(member, dest_path.parent)
                            break
            else:  # .gz
                with gzip.open(tmp_path, "rb") as f_in, open(dest_path, "wb") as f_out:
                    f_out.write(f_in.read())

            tmp_path.unlink(missing_ok=True)
            if config.get("chmod") and dest_path.exists():
                dest_path.chmod(0o755)
            return dest_path.exists()
        except Exception as e:
            self.log(f"install_special_tool({name}) failed: {e}")
            return False
