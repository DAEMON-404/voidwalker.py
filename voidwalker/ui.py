"""Terminal UI: banners, menus, animations and progress widgets.

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


class UIMixin:
    def clear_screen(self):
        print("\033[2J\033[H", end="")

    def hide_cursor(self):
        print("\033[?25l", end="")

    def show_cursor(self):
        print("\033[?25h", end="")

    def print_centered(self, text: str):
        import re
        clean_text = re.sub(r'\033\[[0-9;]*m', '', text)
        padding = (self.term_width - len(clean_text)) // 2
        print(" " * max(0, padding) + text)

    def typing_effect(self, text: str, delay: float = 0.02, color: str = Colors.NEON_CYAN):
        for char in text:
            print(f"{color}{char}{Colors.RESET}", end="", flush=True)
            time.sleep(delay)
        print()

    def matrix_rain(self, duration: float = 2.0):
        self.hide_cursor()
        columns = self.term_width
        drops = [random.randint(0, 20) for _ in range(columns)]
        start_time = time.time()
        
        while time.time() - start_time < duration and self.running:
            line = ""
            for i in range(columns):
                if drops[i] > 0:
                    char = random.choice(Symbols.CYBER_CHARS)
                    intensity = min(255, drops[i] * 20)
                    color = f"\033[38;2;0;{intensity};0m"
                    line += f"{color}{char}"
                    drops[i] -= 1
                    if drops[i] <= 0 and random.random() < 0.1:
                        drops[i] = random.randint(5, 20)
                else:
                    line += " "
                    if random.random() < 0.02:
                        drops[i] = random.randint(5, 20)
            print(f"{line}{Colors.RESET}")
            time.sleep(0.05)
        
        self.show_cursor()

    def draw_box(self, title: str, content: List[str], width: int = 60):
        import re
        title_colored = f"{Colors.NEON_MAGENTA}{title}{Colors.RESET}"
        
        top = f"{Colors.ELECTRIC_BLUE}{Symbols.BOX_TL}{Symbols.BOX_H * (width - 2)}{Symbols.BOX_TR}{Colors.RESET}"
        bottom = f"{Colors.ELECTRIC_BLUE}{Symbols.BOX_BL}{Symbols.BOX_H * (width - 2)}{Symbols.BOX_BR}{Colors.RESET}"
        
        self.print_centered(top)
        
        title_clean = re.sub(r'\033\[[0-9;]*m', '', title_colored)
        title_line = f"{Colors.ELECTRIC_BLUE}{Symbols.BOX_V}{Colors.RESET} {title_colored}"
        padding = width - len(title_clean) - 4
        title_line += " " * max(0, padding) + f" {Colors.ELECTRIC_BLUE}{Symbols.BOX_V}{Colors.RESET}"
        self.print_centered(title_line)
        
        separator = f"{Colors.ELECTRIC_BLUE}{Symbols.BOX_V}{Colors.GRAY}{'─' * (width - 2)}{Colors.ELECTRIC_BLUE}{Symbols.BOX_V}{Colors.RESET}"
        self.print_centered(separator)
        
        for line in content:
            clean_len = len(re.sub(r'\033\[[0-9;]*m', '', line))
            padding = width - clean_len - 4
            padded_line = f"{Colors.ELECTRIC_BLUE}{Symbols.BOX_V}{Colors.RESET} {line}" + " " * max(0, padding) + f" {Colors.ELECTRIC_BLUE}{Symbols.BOX_V}{Colors.RESET}"
            self.print_centered(padded_line)
        
        self.print_centered(bottom)

    def animated_progress_bar(self, current: int, total: int, width: int = 40, label: str = "", item_name: str = ""):
        percentage = current / total if total > 0 else 0
        filled = int(width * percentage)
        
        bar = ""
        for i in range(width):
            if i < filled:
                if i == filled - 1:
                    bar += f"{Colors.NEON_CYAN}{Symbols.BLOCK_DARK}"
                else:
                    bar += f"{Colors.NEON_GREEN}{Symbols.BLOCK_FULL}"
            else:
                bar += f"{Colors.GRAY}{Symbols.BLOCK_LIGHT}"
        
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner = spinner_chars[int(time.time() * 10) % len(spinner_chars)]
        
        item_display = f" {Colors.WHITE}{item_name[:25]:<25}{Colors.RESET}" if item_name else ""
        count_display = f"{Colors.GRAY}[{current}/{total}]{Colors.RESET}"
        
        status = f"\r{Colors.NEON_MAGENTA}{spinner}{Colors.RESET} [{bar}{Colors.RESET}] {Colors.NEON_CYAN}{percentage*100:5.1f}%{Colors.RESET} {count_display}{item_display}"
        if label:
            status = f"\r{Colors.ELECTRIC_BLUE}{label:8}{Colors.RESET} {Colors.NEON_MAGENTA}{spinner}{Colors.RESET} [{bar}{Colors.RESET}] {Colors.NEON_CYAN}{percentage*100:5.1f}%{Colors.RESET} {count_display}{item_display}"
        
        print(status + " " * 10, end="", flush=True)

    def spinner_animation(self, message: str, done_event: threading.Event):
        frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        colors = [Colors.NEON_CYAN, Colors.ELECTRIC_BLUE, Colors.NEON_MAGENTA]
        i = 0
        while not done_event.is_set():
            frame = frames[i % len(frames)]
            color = colors[i % len(colors)]
            print(f"\r{color}{frame}{Colors.RESET} {Colors.NEON_CYAN}{message}{Colors.RESET}" + " " * 20, end="", flush=True)
            time.sleep(0.08)
            i += 1
        print("\r" + " " * 80 + "\r", end="")

    def show_live_status(self, category: str, current: int, total: int, item: str, status: str = "downloading"):
        spinner_chars = ["◐", "◓", "◑", "◒"]
        spinner = spinner_chars[int(time.time() * 8) % len(spinner_chars)]
        
        status_colors = {
            "downloading": Colors.YELLOW,
            "success": Colors.NEON_GREEN,
            "failed": Colors.BRIGHT_RED,
            "cloning": Colors.ELECTRIC_BLUE,
        }
        status_icons = {
            "downloading": "↓",
            "success": Symbols.CHECK,
            "failed": Symbols.CROSS,
            "cloning": "⟳",
        }
        
        color = status_colors.get(status, Colors.WHITE)
        icon = status_icons.get(status, "•")
        
        progress = f"{current}/{total}"
        bar_width = 20
        filled = int(bar_width * (current / total)) if total > 0 else 0
        bar = f"{Colors.NEON_GREEN}{'█' * filled}{Colors.GRAY}{'░' * (bar_width - filled)}{Colors.RESET}"
        
        line = f"\r  {Colors.NEON_MAGENTA}{spinner}{Colors.RESET} {Colors.ELECTRIC_BLUE}{category:18}{Colors.RESET} [{bar}] {Colors.GRAY}{progress:>7}{Colors.RESET}  {color}{icon} {item[:30]:<30}{Colors.RESET}"
        print(line + " " * 10, end="", flush=True)

    def complete_status_line(self, category: str, success: int, failed: int):
        total = success + failed
        bar_width = 20
        bar = f"{Colors.NEON_GREEN}{'█' * bar_width}{Colors.RESET}"
        
        result = f"{Colors.NEON_GREEN}{Symbols.CHECK} {success}{Colors.RESET}"
        if failed > 0:
            result += f" {Colors.BRIGHT_RED}{Symbols.CROSS} {failed}{Colors.RESET}"
        
        line = f"\r  {Colors.NEON_GREEN}{Symbols.CHECK}{Colors.RESET} {Colors.ELECTRIC_BLUE}{category:18}{Colors.RESET} [{bar}] {Colors.GRAY}{total:>3} tools{Colors.RESET}  {result}"
        print(line + " " * 20)

    def download_with_animation(self, name: str, download_func, *args) -> bool:
        done_event = threading.Event()
        result = [False]
        
        def do_download():
            result[0] = download_func(*args)
            done_event.set()
        
        download_thread = threading.Thread(target=do_download)
        download_thread.start()
        
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        while not done_event.is_set():
            frame = frames[i % len(frames)]
            color = [Colors.NEON_CYAN, Colors.ELECTRIC_BLUE, Colors.NEON_MAGENTA][i % 3]
            print(f"\r      {color}{frame}{Colors.RESET} {Colors.GRAY}{name[:50]}{Colors.RESET}" + " " * 20, end="", flush=True)
            time.sleep(0.08)
            i += 1
        
        download_thread.join()
        return result[0]

    def show_ascii_banner(self):
        banner = f"""
{Colors.NEON_CYAN}██╗   ██╗ ██████╗ ██╗██████╗ {Colors.NEON_MAGENTA}██╗    ██╗ █████╗ ██╗     ██╗  ██╗███████╗██████╗ 
{Colors.NEON_CYAN}██║   ██║██╔═══██╗██║██╔══██╗{Colors.NEON_MAGENTA}██║    ██║██╔══██╗██║     ██║ ██╔╝██╔════╝██╔══██╗
{Colors.NEON_CYAN}██║   ██║██║   ██║██║██║  ██║{Colors.NEON_MAGENTA}██║ █╗ ██║███████║██║     █████╔╝ █████╗  ██████╔╝
{Colors.NEON_CYAN}╚██╗ ██╔╝██║   ██║██║██║  ██║{Colors.NEON_MAGENTA}██║███╗██║██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗
{Colors.NEON_CYAN} ╚████╔╝ ╚██████╔╝██║██████╔╝{Colors.NEON_MAGENTA}╚███╔███╔╝██║  ██║███████╗██║  ██╗███████╗██║  ██║
{Colors.NEON_CYAN}  ╚═══╝   ╚═════╝ ╚═╝╚═════╝ {Colors.NEON_MAGENTA} ╚══╝╚══╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
{Colors.RESET}"""
        
        for line in banner.split('\n'):
            self.print_centered(line)
            time.sleep(0.05)
        
        subtitle = f"{Colors.ELECTRIC_BLUE}{'═' * 15} {Colors.NEON_GREEN}Elite Penetration Testing Arsenal {Colors.NEON_MAGENTA}v{__version__} {Colors.ELECTRIC_BLUE}{'═' * 15}{Colors.RESET}"
        self.print_centered(subtitle)
        print()
        
        platform_tag = "Linux & macOS" if sys.platform == "darwin" else "Linux & macOS"
        tagline = f"{Colors.GRAY}[ {Colors.NEON_CYAN}300+ Security Tools for {platform_tag} {Colors.GRAY}]{Colors.RESET}"
        self.print_centered(tagline)
        print()

    def show_skull_art(self):
        skull = f"""
{Colors.BRIGHT_RED}              ██████████████████            
{Colors.BRIGHT_RED}          ████{Colors.WHITE}░░░░░░░░░░░░░░░░{Colors.BRIGHT_RED}████        
{Colors.BRIGHT_RED}        ██{Colors.WHITE}░░░░░░░░░░░░░░░░░░░░░░{Colors.BRIGHT_RED}██      
{Colors.BRIGHT_RED}      ██{Colors.WHITE}░░░░░░░░░░░░░░░░░░░░░░░░░░{Colors.BRIGHT_RED}██    
{Colors.BRIGHT_RED}    ██{Colors.WHITE}░░░░░░{Colors.NEON_CYAN}████{Colors.WHITE}░░░░░░░░{Colors.NEON_CYAN}████{Colors.WHITE}░░░░░░{Colors.BRIGHT_RED}██  
{Colors.BRIGHT_RED}    ██{Colors.WHITE}░░░░░░{Colors.NEON_CYAN}████{Colors.WHITE}░░░░░░░░{Colors.NEON_CYAN}████{Colors.WHITE}░░░░░░{Colors.BRIGHT_RED}██  
{Colors.BRIGHT_RED}    ██{Colors.WHITE}░░░░░░░░░░░░░░░░░░░░░░░░░░░░{Colors.BRIGHT_RED}██  
{Colors.BRIGHT_RED}    ██{Colors.WHITE}░░░░░░░░░░░░{Colors.NEON_MAGENTA}████{Colors.WHITE}░░░░░░░░░░░░{Colors.BRIGHT_RED}██  
{Colors.BRIGHT_RED}      ██{Colors.WHITE}░░░░░░░░░░░░░░░░░░░░░░░░{Colors.BRIGHT_RED}██    
{Colors.BRIGHT_RED}        ██{Colors.WHITE}░░{Colors.NEON_GREEN}██{Colors.WHITE}░░{Colors.NEON_GREEN}██{Colors.WHITE}░░{Colors.NEON_GREEN}██{Colors.WHITE}░░{Colors.NEON_GREEN}██{Colors.WHITE}░░{Colors.BRIGHT_RED}██      
{Colors.BRIGHT_RED}          ████████████████████████        
{Colors.RESET}"""
        for line in skull.split('\n'):
            self.print_centered(line)
            time.sleep(0.03)

    def show_intro_animation(self):
        self.clear_screen()
        self.hide_cursor()
        self.matrix_rain(1.5)
        self.clear_screen()
        self.show_ascii_banner()
        time.sleep(0.5)
        self.show_skull_art()
        print()
        
        warnings = [
            f"{Colors.BRIGHT_RED}{Symbols.LIGHTNING} AUTHORIZED USE ONLY {Symbols.LIGHTNING}{Colors.RESET}",
            f"{Colors.YELLOW}For educational and authorized security testing purposes{Colors.RESET}",
            f"{Colors.GRAY}Requires root/sudo privileges for installation{Colors.RESET}",
        ]
        for warning in warnings:
            self.print_centered(warning)
            time.sleep(0.2)
        
        print()
        self.show_cursor()

    def show_main_menu(self) -> str:
        print()
        menu_items = [
            (f"{Symbols.ROCKET}", "Install Full Arsenal (350+ tools)", "full"),
            (f"{Symbols.GEAR}", "Select Categories", "categories"),
            (f"{Symbols.STAR}", "View All Tools", "list"),
            (f"{Symbols.CHECK}", "System Packages (apt/brew)", "apt"),
            (f"{Symbols.LIGHTNING}", "Install Metasploit (msfconsole)", "metasploit"),
            (f"{Symbols.STAR}", "Install AI Code Agents (claude / codex)", "aiclis"),
            (f"{Symbols.DIAMOND}", "Windows Binaries Only", "windows"),
            (f"{Symbols.LIGHTNING}", "Build C# Tools from Source", "build"),
            (f"{Symbols.SHIELD}", "Setup Pentest Obsidian Vault", "vault"),
            (f"{Symbols.GEAR}", "Fix / Harden Kali (pimpmykali)", "kalifix"),
            (f"{Symbols.DIAMOND}", "Deploy Pentest Environment (pe)", "pentestenv"),
            (f"{Symbols.SHIELD}", "Setup BloodHound-CE", "bloodhound"),
            (f"{Symbols.GEAR}", "Proxy / Pivot Helper", "proxy"),
            (f"{Symbols.SHIELD}", "Root Setup (red prompt + your tools as root)", "rootsetup"),
            (f"{Symbols.STAR}", "Engagement Logging / Evidence", "rec"),
            (f"{Symbols.SHIELD}", "View Sources & Guides", "sources"),
            (f"{Symbols.CROSS}", "Exit", "exit"),
        ]
        
        content = []
        for i, (icon, label, _) in enumerate(menu_items, 1):
            if i == len(menu_items):
                content.append(f"{Colors.BRIGHT_RED}[{i}] {icon} {label}{Colors.RESET}")
            else:
                content.append(f"{Colors.NEON_CYAN}[{i}] {Colors.NEON_GREEN}{icon} {Colors.WHITE}{label}{Colors.RESET}")
        
        self.draw_box(f"{Symbols.SHIELD} MAIN MENU", content, 55)
        print()
        
        while True:
            prompt = f"{Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} Select option {Colors.GRAY}[1-{len(menu_items)}]{Colors.RESET}: "
            try:
                choice = input(prompt).strip()
                if choice.isdigit() and 1 <= int(choice) <= len(menu_items):
                    return menu_items[int(choice) - 1][2]
                print(f"{Colors.BRIGHT_RED}Invalid option. Please try again.{Colors.RESET}")
            except EOFError:
                return "exit"

    def show_category_menu(self) -> List[str]:
        print()
        categories = list(TOOL_CATEGORIES.keys())
        content = []
        for i, cat in enumerate(categories, 1):
            desc = TOOL_CATEGORIES[cat].get("description", "")[:40]
            content.append(f"{Colors.NEON_CYAN}[{i:2}] {Colors.WHITE}{cat}{Colors.RESET}")
            content.append(f"     {Colors.GRAY}{desc}...{Colors.RESET}")
        content.append(f"{Colors.NEON_GREEN}[A ] All Categories{Colors.RESET}")
        content.append(f"{Colors.BRIGHT_RED}[B ] Back to Main Menu{Colors.RESET}")
        
        self.draw_box(f"{Symbols.GEAR} SELECT CATEGORIES", content, 60)
        print()
        
        prompt = f"{Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} Enter selections {Colors.GRAY}(comma-separated, e.g., 1,3,5){Colors.RESET}: "
        try:
            choice = input(prompt).strip().upper()
        except EOFError:
            return []
        
        if choice == 'B':
            return []
        if choice == 'A':
            return categories
        
        selected = []
        for part in choice.split(','):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(categories):
                    selected.append(categories[idx])
        
        return selected

    def show_tool_list(self):
        print()
        for category, data in TOOL_CATEGORIES.items():
            print(f"\n  {Colors.NEON_MAGENTA}{Symbols.DIAMOND} {category}{Colors.RESET}")
            print(f"  {Colors.GRAY}{'─' * 60}{Colors.RESET}")
            print(f"  {Colors.ELECTRIC_BLUE}{data.get('description', '')}{Colors.RESET}")
            
            if 'tools' in data:
                for tool in data['tools'][:5]:
                    print(f"    {Colors.NEON_CYAN}{Symbols.ARROW_RIGHT}{Colors.RESET} {Colors.WHITE}{tool[0]:20}{Colors.RESET} {Colors.GRAY}{tool[3][:35]}...{Colors.RESET}")
                if len(data['tools']) > 5:
                    print(f"    {Colors.GRAY}... and {len(data['tools']) - 5} more{Colors.RESET}")
            
            if 'repos' in data:
                print(f"    {Colors.YELLOW}+ {len(data['repos'])} Git repositories{Colors.RESET}")

        # Sources, Guides & References
        print(f"\n  {Colors.NEON_MAGENTA}{Symbols.SHIELD} Sources, Guides & Cheatsheets{Colors.RESET}")
        print(f"  {Colors.GRAY}{'─' * 60}{Colors.RESET}")
        for section, entries in SOURCES_AND_GUIDES.items():
            print(f"    {Colors.NEON_CYAN}{Symbols.ARROW_RIGHT}{Colors.RESET} {Colors.WHITE}{section}{Colors.RESET} {Colors.GRAY}({len(entries)} entries){Colors.RESET}")

        print()
        input(f"{Colors.GRAY}Press Enter to continue...{Colors.RESET}")

    def show_sources(self):
        self.clear_screen()
        self.show_ascii_banner()
        print()
        self.print_centered(f"{Colors.NEON_MAGENTA}{Symbols.SHIELD} SOURCES, GUIDES & CHEATSHEETS {Symbols.SHIELD}{Colors.RESET}")
        self.print_centered(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
        print()
        
        for section, entries in SOURCES_AND_GUIDES.items():
            print(f"  {Colors.NEON_MAGENTA}{Symbols.DIAMOND} {section}{Colors.RESET}")
            print(f"  {Colors.GRAY}{'─' * 60}{Colors.RESET}")
            for name, url in entries:
                print(f"    {Colors.NEON_CYAN}{Symbols.ARROW_RIGHT}{Colors.RESET} {Colors.WHITE}{name:40}{Colors.RESET}")
                print(f"      {Colors.ELECTRIC_BLUE}{url}{Colors.RESET}")
            print()
            
        input(f"{Colors.GRAY}Press Enter to return to main menu...{Colors.RESET}")

    def show_installation_preview(self, categories: List[str]) -> bool:
        self.clear_screen()
        self.show_ascii_banner()
        
        print()
        self.print_centered(f"{Colors.NEON_MAGENTA}{Symbols.ROCKET} INSTALLATION PREVIEW {Symbols.ROCKET}{Colors.RESET}")
        self.print_centered(f"{Colors.ELECTRIC_BLUE}{'─' * 50}{Colors.RESET}")
        print()
        
        total_tools = 0
        total_repos = 0
        total_files = 0
        
        for cat in categories:
            if cat in TOOL_CATEGORIES:
                data = TOOL_CATEGORIES[cat]
                total_tools += len(data.get('tools', []))
                total_repos += len(data.get('repos', []))
                total_files += len(data.get('files', []))
        
        stats_line = f"{Colors.NEON_CYAN}Categories: {len(categories)}{Colors.RESET} | "
        stats_line += f"{Colors.NEON_GREEN}Binaries: {total_tools}{Colors.RESET} | "
        stats_line += f"{Colors.YELLOW}Repos: {total_repos}{Colors.RESET} | "
        stats_line += f"{Colors.NEON_MAGENTA}Files: {total_files}{Colors.RESET}"
        self.print_centered(stats_line)
        print()
        
        for cat in categories:
            if cat not in TOOL_CATEGORIES:
                continue
            data = TOOL_CATEGORIES[cat]
            
            print(f"  {Colors.NEON_MAGENTA}{Symbols.DIAMOND} {cat}{Colors.RESET}")
            print(f"  {Colors.GRAY}{'─' * 60}{Colors.RESET}")
            
            items = []
            if 'tools' in data:
                for tool in data['tools'][:3]:
                    items.append(f"    {Colors.NEON_GREEN}{Symbols.ARROW_RIGHT}{Colors.RESET} {tool[0]} - {Colors.GRAY}{tool[3][:40]}{Colors.RESET}")
                if len(data['tools']) > 3:
                    items.append(f"    {Colors.GRAY}... +{len(data['tools']) - 3} more binaries{Colors.RESET}")
            
            if 'repos' in data:
                items.append(f"    {Colors.YELLOW}+ {len(data['repos'])} Git repos to clone{Colors.RESET}")
            
            for item in items:
                print(item)
            print()
        
        print(f"  {Colors.ELECTRIC_BLUE}{'═' * 60}{Colors.RESET}")
        print()
        
        try:
            prompt = f"{Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} Proceed with installation? {Colors.GRAY}[Y/n]{Colors.RESET}: "
            choice = input(prompt).strip().lower()
            return choice != 'n'
        except EOFError:
            return False

