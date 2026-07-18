"""Core orchestration methods mixed into the VoidWalker class.

Auto-extracted from the original monolithic voidwalker.py; method bodies are
unchanged except where noted. Part of the VoidWalker package refactor.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import random
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from .version import __version__
from .theme import Colors, Symbols
from .hostinfo import HostInfo, select_asset
from .data.workspace import WORKSPACE_DIRS
from .data.catalog import TOOL_CATEGORIES
from .data.packages import (
    APT_TOOLS, BREW_TOOLS, BREW_CASKS, PIPX_TOOLS,
    GO_TOOLS, CARGO_TOOLS, GEM_TOOLS, UV_TOOLS,
)
from .data.binaries import CROSS_PLATFORM_TOOLS, SPECIAL_TOOLS
from .data.build_targets import BUILD_TARGETS
from .data.sources import SOURCES_AND_GUIDES


class _CoreMethods:
    def log(self, message: str):
        """Append a message to the log file with a timestamp."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    def signal_handler(self, sig, frame):
        self.running = False
        self.clear_screen()
        self.print_centered(f"{Colors.BRIGHT_RED}Installation interrupted!{Colors.RESET}")
        print()
        sys.exit(0)

    def install_category(self, category: str):
        if category not in TOOL_CATEGORIES:
            return
        
        data = TOOL_CATEGORIES[category]
        base_dir = self.base_path / "tools"
        dest = base_dir / category.lower().replace(" ", "_").replace("&", "and")
        
        all_items = []
        if 'tools' in data:
            for item in data['tools']:
                all_items.append(('tool', item[0], item[1], item[2]))
        if 'files' in data:
            for item in data['files']:
                all_items.append(('file', item[0], 'file', item[1]))
        if 'repos' in data:
            for item in data['repos']:
                all_items.append(('repo', item[0], 'git', item[1]))

        # Honour a category's `special` key (cross-platform binaries such as
        # chisel/ligolo-ng), which the old generic loop silently ignored.
        if data.get('special'):
            self.install_cross_platform_tools(only=set(data['special']))

        if not all_items:
            return
        
        cat_success, cat_fail = 0, 0
        total_items = len(all_items)
        short_name = category[:18] if len(category) > 18 else category
        
        def download_worker(item):
            item_type, name, method, url = item
            if item_type == 'tool':
                if method == "file": return self.download_file(url, dest / name)
                elif method == "zip": return self.download_and_extract_zip(url, dest / name.lower())
                elif method == "git": return self.git_clone(url, dest / name)
            elif item_type == 'file':
                return self.download_file(url, dest / name)
            elif item_type == 'repo':
                return self.git_clone(url, dest / name)
            return False

        completed = 0
        self.show_live_status(short_name, completed, total_items, "Starting threads...", "downloading")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_item = {executor.submit(download_worker, item): item for item in all_items}
            for future in as_completed(future_to_item):
                completed += 1
                if future.result():
                    cat_success += 1
                    self.stats["ok"] += 1
                else:
                    cat_fail += 1
                    self.stats["fail"] += 1
                
                self.show_live_status(short_name, completed, total_items, f"Processing {completed}/{total_items}", "downloading")
        
        self.complete_status_line(short_name, cat_success, cat_fail)

    def install_full_arsenal(self):
        categories = list(TOOL_CATEGORIES.keys())
        if not self.show_installation_preview(categories):
            print(f"\n{Colors.YELLOW}Installation cancelled.{Colors.RESET}")
            time.sleep(1)
            return
        
        self.clear_screen()
        self.show_ascii_banner()
        
        print()
        self.print_centered(f"{Colors.NEON_MAGENTA}{Symbols.ROCKET} FULL ARSENAL INSTALLATION {Symbols.ROCKET}{Colors.RESET}")
        print()
        
        for d in WORKSPACE_DIRS:
            (self.base_path / d).mkdir(parents=True, exist_ok=True)
        print(f"  {Colors.NEON_GREEN}{Symbols.CHECK} Workspace created at {self.base_path}{Colors.RESET}")
        
        self.install_system_tools()
        
        for category in categories:
            self.install_category(category)
        
        print()
        self.show_summary()

    def install_categories(self, categories: List[str]):
        if not self.show_installation_preview(categories):
            print(f"\n{Colors.YELLOW}Installation cancelled.{Colors.RESET}")
            time.sleep(1)
            return
        
        self.clear_screen()
        self.show_ascii_banner()
        
        print()
        self.print_centered(f"{Colors.NEON_MAGENTA}{Symbols.ROCKET} INSTALLING SELECTED CATEGORIES {Symbols.ROCKET}{Colors.RESET}")
        print()
        
        for d in WORKSPACE_DIRS:
            (self.base_path / d).mkdir(parents=True, exist_ok=True)
        
        for category in categories:
            self.install_category(category)
        
        print()
        self.show_summary()

    def show_summary(self):
        print()
        self.print_centered(f"{Colors.NEON_MAGENTA}{'═' * 50}{Colors.RESET}")
        self.print_centered(f"{Colors.NEON_CYAN}{Symbols.STAR} INSTALLATION COMPLETE {Symbols.STAR}{Colors.RESET}")
        self.print_centered(f"{Colors.NEON_MAGENTA}{'═' * 50}{Colors.RESET}")
        print()
        
        stats = [
            f"{Colors.NEON_GREEN}{Symbols.CHECK} Successful: {self.stats['ok']}{Colors.RESET}",
            f"{Colors.BRIGHT_RED}{Symbols.CROSS} Failed: {self.stats['fail']}{Colors.RESET}",
            f"{Colors.ELECTRIC_BLUE}Tools installed to: {self.base_path}{Colors.RESET}",
        ]
        
        self.draw_box(f"{Symbols.SHIELD} SUMMARY", stats, 50)
        print()
        
        input(f"{Colors.GRAY}Press Enter to continue...{Colors.RESET}")

    def run(self):
        self.show_intro_animation()
        
        while self.running:
            choice = self.show_main_menu()
            
            if choice == "exit":
                self.clear_screen()
                self.print_centered(f"{Colors.NEON_MAGENTA}")
                self.print_centered("╔═══════════════════════════════════════════╗")
                self.print_centered("║       Thanks for using VoidWalker!        ║")
                self.print_centered("║        Stay safe, hack responsibly        ║")
                self.print_centered("╚═══════════════════════════════════════════╝")
                print(Colors.RESET)
                break
            
            elif choice == "full":
                self.install_full_arsenal()
            
            elif choice == "categories":
                selected = self.show_category_menu()
                if selected:
                    self.install_categories(selected)
            
            elif choice == "list":
                self.show_tool_list()
            
            elif choice == "apt":
                self.install_system_tools()

            elif choice == "metasploit":
                self.install_metasploit()

            elif choice == "aiclis":
                self.install_ai_clis()

            elif choice == "windows":
                self.install_windows_binaries()

            elif choice == "build":
                self.build_all_tools()

            elif choice == "vault":
                self.setup_obsidian_vault()

            elif choice == "kalifix":
                self.kali_fix_menu()

            elif choice == "pentestenv":
                self.pentest_env_menu()

            elif choice == "bloodhound":
                self.bloodhound_menu()

            elif choice == "proxy":
                self.proxy_menu()

            elif choice == "rootsetup":
                self.root_setup_menu()

            elif choice == "rec":
                self.run_recorder_menu()

            elif choice == "sources":
                self.show_sources()

