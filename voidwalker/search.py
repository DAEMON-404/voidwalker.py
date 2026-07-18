"""Offline/online search helpers and the interactive dork generator."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError

from .theme import Colors, Symbols


def search_poc(query: str):
    """Search for PoC exploits on GitHub."""
    print(f"\n{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}")
    print(f"{Colors.NEON_CYAN}  {Symbols.LIGHTNING} VoidWalker PoC Search {Symbols.LIGHTNING}{Colors.RESET}")
    print(f"{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}")
    print(f"\n  {Colors.ELECTRIC_BLUE}Searching for:{Colors.RESET} {Colors.WHITE}{query}{Colors.RESET}\n")
    
    base_path = Path.home() / "voidwalker" / "tools" / "exploit_frameworks" / "PoC-in-GitHub"
    
    if not base_path.exists():
        print(f"  {Colors.YELLOW}{Symbols.CIRCLE} PoC repository not found.{Colors.RESET}")
        print(f"  {Colors.GRAY}Run VoidWalker installer first to download exploit databases.{Colors.RESET}")
        print(f"\n  {Colors.NEON_CYAN}Searching GitHub API instead...{Colors.RESET}\n")
        
        try:
            api_url = f"https://api.github.com/search/repositories?q={query}+poc+exploit&sort=updated&per_page=20"
            req = urllib.request.Request(api_url, headers={"User-Agent": "VoidWalker/3.9.2"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                
            if data.get("items"):
                print(f"  {Colors.NEON_GREEN}Found {len(data['items'])} results:{Colors.RESET}\n")
                for i, item in enumerate(data["items"][:15], 1):
                    stars = item.get("stargazers_count", 0)
                    star_color = Colors.YELLOW if stars > 100 else Colors.GRAY
                    print(f"  {Colors.NEON_CYAN}[{i:2}]{Colors.RESET} {Colors.WHITE}{item['full_name']}{Colors.RESET}")
                    print(f"      {star_color}{Symbols.STAR} {stars}{Colors.RESET} | {Colors.GRAY}{item.get('description', 'No description')[:60]}{Colors.RESET}")
                    print(f"      {Colors.ELECTRIC_BLUE}{item['html_url']}{Colors.RESET}\n")
            else:
                print(f"  {Colors.BRIGHT_RED}No results found for '{query}'{Colors.RESET}")
        except Exception as e:
            print(f"  {Colors.BRIGHT_RED}API search failed: {e}{Colors.RESET}")
        return
    
    print(f"  {Colors.NEON_GREEN}Searching local PoC database...{Colors.RESET}\n")
    
    results = []
    query_lower = query.lower()
    
    for year_dir in base_path.iterdir():
        if year_dir.is_dir() and year_dir.name.isdigit():
            for cve_dir in year_dir.iterdir():
                if query_lower in cve_dir.name.lower():
                    readme = cve_dir / "README.md"
                    if readme.exists():
                        try:
                            content = readme.read_text()[:500]
                            urls = re.findall(r'https://github\.com/[^\s\)]+', content)
                            results.append((cve_dir.name, urls[:3], str(cve_dir)))
                        except:
                            results.append((cve_dir.name, [], str(cve_dir)))
    
    if results:
        print(f"  {Colors.NEON_GREEN}Found {len(results)} matching CVEs:{Colors.RESET}\n")
        for cve, urls, path in results[:20]:
            print(f"  {Colors.NEON_CYAN}{Symbols.DIAMOND}{Colors.RESET} {Colors.WHITE}{cve}{Colors.RESET}")
            for url in urls:
                print(f"      {Colors.ELECTRIC_BLUE}{url}{Colors.RESET}")
            print(f"      {Colors.GRAY}Local: {path}{Colors.RESET}\n")
    else:
        print(f"  {Colors.YELLOW}No local results. Trying GitHub API...{Colors.RESET}\n")
        try:
            api_url = f"https://api.github.com/search/repositories?q={query}+poc+exploit&sort=updated&per_page=15"
            req = urllib.request.Request(api_url, headers={"User-Agent": "VoidWalker/3.9.2"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data.get("items"):
                for item in data["items"][:10]:
                    print(f"  {Colors.NEON_CYAN}{Symbols.DIAMOND}{Colors.RESET} {Colors.WHITE}{item['full_name']}{Colors.RESET}")
                    print(f"      {Colors.ELECTRIC_BLUE}{item['html_url']}{Colors.RESET}\n")
        except:
            print(f"  {Colors.BRIGHT_RED}No results found.{Colors.RESET}")
    
    print(f"{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}\n")


def search_nse(query: str):
    """Search for Nmap NSE scripts."""
    print(f"\n{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}")
    print(f"{Colors.NEON_CYAN}  {Symbols.GEAR} VoidWalker NSE Script Search {Symbols.GEAR}{Colors.RESET}")
    print(f"{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}")
    print(f"\n  {Colors.ELECTRIC_BLUE}Searching for:{Colors.RESET} {Colors.WHITE}{query}{Colors.RESET}\n")
    
    nse_paths = [
        Path("/usr/share/nmap/scripts"),
        Path("/usr/local/share/nmap/scripts"),
        Path.home() / "nmap" / "scripts",
    ]
    
    nse_dir = None
    for path in nse_paths:
        if path.exists():
            nse_dir = path
            break
    
    if not nse_dir:
        print(f"  {Colors.YELLOW}{Symbols.CIRCLE} Nmap scripts directory not found.{Colors.RESET}")
        print(f"  {Colors.GRAY}Install nmap first: sudo apt install nmap{Colors.RESET}")
        print(f"\n  {Colors.NEON_CYAN}Showing common scripts for '{query}'...{Colors.RESET}\n")
        
        common_scripts = {
            "http": ["http-enum", "http-vuln-*", "http-shellshock", "http-sql-injection", "http-headers", "http-methods", "http-title", "http-robots.txt"],
            "smb": ["smb-enum-shares", "smb-enum-users", "smb-vuln-*", "smb-os-discovery", "smb-protocols", "smb2-vuln-uptime"],
            "ssh": ["ssh-brute", "ssh-auth-methods", "ssh-hostkey", "ssh2-enum-algos"],
            "ftp": ["ftp-anon", "ftp-bounce", "ftp-brute", "ftp-vuln-*"],
            "dns": ["dns-brute", "dns-zone-transfer", "dns-cache-snoop", "dns-recursion"],
            "mysql": ["mysql-brute", "mysql-enum", "mysql-vuln-*", "mysql-info"],
            "ldap": ["ldap-search", "ldap-brute", "ldap-rootdse"],
            "vuln": ["vulners", "vulscan", "smb-vuln-*", "http-vuln-*", "ssl-heartbleed", "ssl-poodle"],
            "ssl": ["ssl-cert", "ssl-enum-ciphers", "ssl-heartbleed", "ssl-poodle", "sslv2"],
            "snmp": ["snmp-brute", "snmp-info", "snmp-sysdescr", "snmp-processes"],
            "rdp": ["rdp-enum-encryption", "rdp-vuln-ms12-020", "rdp-ntlm-info"],
            "default": ["default", "discovery", "safe", "vuln", "exploit", "brute", "auth"],
        }
        
        query_lower = query.lower()
        matches = common_scripts.get(query_lower, [])
        
        if not matches:
            for cat, scripts in common_scripts.items():
                for script in scripts:
                    if query_lower in script.lower():
                        matches.append(script)
        
        if matches:
            print(f"  {Colors.NEON_GREEN}Suggested scripts:{Colors.RESET}\n")
            for script in matches[:15]:
                print(f"  {Colors.NEON_CYAN}{Symbols.ARROW_RIGHT}{Colors.RESET} {Colors.WHITE}{script}{Colors.RESET}")
            print(f"\n  {Colors.GRAY}Usage: nmap --script={matches[0]} <target>{Colors.RESET}")
        else:
            print(f"  {Colors.GRAY}Try: http, smb, ssh, ftp, dns, vuln, ssl, mysql, ldap{Colors.RESET}")
        
        print(f"\n{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}\n")
        return
    
    print(f"  {Colors.NEON_GREEN}Searching {nse_dir}...{Colors.RESET}\n")
    
    results = []
    query_lower = query.lower()
    
    for script in nse_dir.glob("*.nse"):
        if query_lower in script.name.lower():
            try:
                content = script.read_text()[:1000]
                desc_match = re.search(r'description\s*=\s*[\[\{]*(.*?)[\]\}]*,?\s*(?:categories|author)', content, re.DOTALL | re.IGNORECASE)
                desc = desc_match.group(1).strip()[:100] if desc_match else ""
                desc = re.sub(r'[\[\]"\'\n]', '', desc).strip()
                results.append((script.name, desc))
            except:
                results.append((script.name, ""))
    
    if results:
        print(f"  {Colors.NEON_GREEN}Found {len(results)} scripts:{Colors.RESET}\n")
        for name, desc in sorted(results)[:25]:
            print(f"  {Colors.NEON_CYAN}{Symbols.ARROW_RIGHT}{Colors.RESET} {Colors.WHITE}{name}{Colors.RESET}")
            if desc:
                print(f"      {Colors.GRAY}{desc[:70]}...{Colors.RESET}")
        
        if results:
            print(f"\n  {Colors.ELECTRIC_BLUE}Example usage:{Colors.RESET}")
            print(f"  {Colors.WHITE}nmap --script={results[0][0].replace('.nse', '')} <target>{Colors.RESET}")
    else:
        print(f"  {Colors.BRIGHT_RED}No scripts found matching '{query}'{Colors.RESET}")
        print(f"  {Colors.GRAY}Try: http, smb, ssh, ftp, dns, vuln, ssl{Colors.RESET}")
    
    print(f"\n{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}\n")


def search_exploitdb(query: str):
    """Search Exploit-DB for exploits."""
    print(f"\n{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}")
    print(f"{Colors.NEON_CYAN}  {Symbols.LIGHTNING} VoidWalker Exploit-DB Search {Symbols.LIGHTNING}{Colors.RESET}")
    print(f"{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}")
    print(f"\n  {Colors.ELECTRIC_BLUE}Searching for:{Colors.RESET} {Colors.WHITE}{query}{Colors.RESET}\n")
    
    local_db = Path.home() / "voidwalker" / "tools" / "exploit_frameworks" / "exploitdb"
    
    if local_db.exists():
        print(f"  {Colors.NEON_GREEN}Searching local Exploit-DB...{Colors.RESET}\n")
        try:
            result = subprocess.run(
                ["grep", "-ri", query, str(local_db / "exploits")],
                capture_output=True, text=True, timeout=30
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')[:20]
                for line in lines:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        filepath = parts[0].replace(str(local_db), "")
                        print(f"  {Colors.NEON_CYAN}{Symbols.ARROW_RIGHT}{Colors.RESET} {Colors.WHITE}{filepath}{Colors.RESET}")
                print(f"\n  {Colors.GRAY}Found {len(lines)} results (showing first 20){Colors.RESET}")
            else:
                print(f"  {Colors.YELLOW}No local results. Searching online...{Colors.RESET}")
        except:
            pass
    
    print(f"\n  {Colors.NEON_CYAN}Querying Exploit-DB API...{Colors.RESET}\n")
    
    try:
        url = f"https://exploits.shodan.io/api/search?query={urllib.parse.quote(query)}&key=public"
        alt_url = f"https://www.exploit-db.com/search?q={urllib.parse.quote(query)}"
        
        print(f"  {Colors.ELECTRIC_BLUE}Search online at:{Colors.RESET}")
        print(f"  {Colors.WHITE}https://www.exploit-db.com/search?q={query}{Colors.RESET}")
        print(f"  {Colors.WHITE}https://sploitus.com/?query={query}{Colors.RESET}")
        print(f"\n  {Colors.GRAY}Or use searchsploit locally:{Colors.RESET}")
        print(f"  {Colors.WHITE}searchsploit {query}{Colors.RESET}")
    except Exception as e:
        print(f"  {Colors.BRIGHT_RED}Search failed: {e}{Colors.RESET}")
    
    print(f"\n{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}\n")


def search_shodan(query: str, api_key: str = None):
    """Search Shodan for hosts."""
    print(f"\n{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}")
    print(f"{Colors.NEON_CYAN}  {Symbols.GEAR} VoidWalker Shodan Search {Symbols.GEAR}{Colors.RESET}")
    print(f"{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}")
    print(f"\n  {Colors.ELECTRIC_BLUE}Searching for:{Colors.RESET} {Colors.WHITE}{query}{Colors.RESET}\n")
    
    if not api_key:
        api_key = os.environ.get("SHODAN_API_KEY")
    
    if not api_key:
        print(f"  {Colors.YELLOW}{Symbols.CIRCLE} No Shodan API key found.{Colors.RESET}")
        print(f"\n  {Colors.GRAY}Set your API key:{Colors.RESET}")
        print(f"  {Colors.WHITE}export SHODAN_API_KEY='your-api-key'{Colors.RESET}")
        print(f"\n  {Colors.GRAY}Or get a free key at:{Colors.RESET}")
        print(f"  {Colors.ELECTRIC_BLUE}https://account.shodan.io/register{Colors.RESET}")
        print(f"\n  {Colors.NEON_CYAN}Showing common Shodan dorks...{Colors.RESET}\n")
        
        dorks = [
            ("Webcams", 'webcam has_screenshot:true'),
            ("Apache servers", 'apache country:US'),
            ("Open MongoDB", 'mongodb port:27017'),
            ("Jenkins", 'jenkins 200 ok'),
            ("Kubernetes", 'kubernetes'),
            ("RDP servers", 'port:3389 has_screenshot:true'),
            ("VNC servers", 'vnc authentication disabled'),
            ("Elastic", 'elastic port:9200'),
            ("FTP anon", 'ftp anonymous'),
            ("Default creds", '"default password"'),
        ]
        
        for name, dork in dorks:
            print(f"  {Colors.NEON_CYAN}{Symbols.ARROW_RIGHT}{Colors.RESET} {Colors.WHITE}{name}:{Colors.RESET} {Colors.GRAY}{dork}{Colors.RESET}")
        
        print(f"\n  {Colors.ELECTRIC_BLUE}Search manually at:{Colors.RESET}")
        print(f"  {Colors.WHITE}https://www.shodan.io/search?query={urllib.parse.quote(query)}{Colors.RESET}")
    else:
        try:
            api_url = f"https://api.shodan.io/shodan/host/search?key={api_key}&query={urllib.parse.quote(query)}"
            req = urllib.request.Request(api_url, headers={"User-Agent": "VoidWalker/3.9.2"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            
            if data.get("matches"):
                print(f"  {Colors.NEON_GREEN}Found {data.get('total', 0)} results:{Colors.RESET}\n")
                for match in data["matches"][:15]:
                    ip = match.get("ip_str", "N/A")
                    port = match.get("port", "N/A")
                    org = match.get("org", "N/A")
                    product = match.get("product", "")
                    country = match.get("location", {}).get("country_name", "")
                    
                    print(f"  {Colors.NEON_CYAN}{Symbols.DIAMOND}{Colors.RESET} {Colors.WHITE}{ip}:{port}{Colors.RESET}")
                    print(f"      {Colors.GRAY}Org: {org} | {country}{Colors.RESET}")
                    if product:
                        print(f"      {Colors.YELLOW}{product}{Colors.RESET}")
                    print()
            else:
                print(f"  {Colors.YELLOW}No results found for '{query}'{Colors.RESET}")
        except Exception as e:
            print(f"  {Colors.BRIGHT_RED}API error: {e}{Colors.RESET}")
    
    print(f"\n{Colors.NEON_MAGENTA}{'═' * 60}{Colors.RESET}\n")


def dork_generator():
    """Interactive Google Dork generator TUI."""
    print(f"\n{Colors.NEON_MAGENTA}{'═' * 70}{Colors.RESET}")
    print(f"{Colors.NEON_CYAN}  {Symbols.STAR} VoidWalker Google Dork Generator {Symbols.STAR}{Colors.RESET}")
    print(f"{Colors.NEON_MAGENTA}{'═' * 70}{Colors.RESET}\n")
    
    while True:
        print(f"  {Colors.ELECTRIC_BLUE}Select dork type:{Colors.RESET}\n")
        
        options = [
            ("1", "inurl", "Search in URL path"),
            ("2", "intext", "Search in page content"),
            ("3", "intitle", "Search in page title"),
            ("4", "filetype", "Search for file types (pdf, xls, doc, sql, log)"),
            ("5", "site", "Search within specific site"),
            ("6", "ext", "Search by file extension"),
            ("7", "cache", "View cached version"),
            ("8", "link", "Find pages linking to URL"),
            ("9", "Sensitive Files", "Pre-built dorks for sensitive files"),
            ("10", "Login Pages", "Pre-built dorks for login pages"),
            ("11", "Exposed Databases", "Pre-built dorks for databases"),
            ("12", "Config Files", "Pre-built dorks for configs"),
            ("13", "Vulnerable Servers", "Pre-built dorks for vulnerable servers"),
            ("14", "Custom Combine", "Combine multiple operators"),
            ("0", "Exit", "Return to main menu"),
        ]
        
        for num, name, desc in options:
            if num == "0":
                print(f"  {Colors.BRIGHT_RED}[{num}]{Colors.RESET} {Colors.GRAY}{desc}{Colors.RESET}")
            else:
                print(f"  {Colors.NEON_CYAN}[{num:2}]{Colors.RESET} {Colors.WHITE}{name:20}{Colors.RESET} {Colors.GRAY}{desc}{Colors.RESET}")
        
        print()
        try:
            choice = input(f"  {Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} Select option: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if choice == "0":
            break
        
        dork = ""
        
        if choice in ["1", "2", "3", "5", "6", "7", "8"]:
            operators = {"1": "inurl", "2": "intext", "3": "intitle", "5": "site", "6": "ext", "7": "cache", "8": "link"}
            op = operators[choice]
            try:
                keyword = input(f"  {Colors.ELECTRIC_BLUE}Enter search term for {op}:{Colors.RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if keyword:
                dork = f'{op}:{keyword}'
        
        elif choice == "4":
            print(f"\n  {Colors.GRAY}Common file types: pdf, doc, docx, xls, xlsx, ppt, sql, log, bak, conf, xml, json, env{Colors.RESET}")
            try:
                filetype = input(f"  {Colors.ELECTRIC_BLUE}Enter file type:{Colors.RESET} ").strip()
                keyword = input(f"  {Colors.ELECTRIC_BLUE}Enter search keyword (optional):{Colors.RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if filetype:
                dork = f'filetype:{filetype}'
                if keyword:
                    dork += f' {keyword}'
        
        elif choice == "9":
            prebuilt = [
                ('Passwords in files', 'filetype:txt intext:password'),
                ('SQL dumps', 'filetype:sql intext:"INSERT INTO"'),
                ('Environment files', 'filetype:env intext:DB_PASSWORD'),
                ('SSH keys', 'filetype:pem intext:"PRIVATE KEY"'),
                ('Backup files', 'filetype:bak | filetype:backup | filetype:old'),
                ('Log files', 'filetype:log intext:password'),
                ('Config files', 'filetype:conf | filetype:config | filetype:cfg'),
                ('Excel with passwords', 'filetype:xls intext:password'),
                ('Git exposed', 'inurl:".git" intitle:"index of"'),
                ('AWS credentials', 'filetype:json intext:aws_access_key_id'),
            ]
            print(f"\n  {Colors.NEON_GREEN}Sensitive File Dorks:{Colors.RESET}\n")
            for i, (name, d) in enumerate(prebuilt, 1):
                print(f"  {Colors.NEON_CYAN}[{i:2}]{Colors.RESET} {Colors.WHITE}{name}{Colors.RESET}")
                print(f"      {Colors.GRAY}{d}{Colors.RESET}")
            
            try:
                sel = input(f"\n  {Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} Select (1-{len(prebuilt)}): ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(prebuilt):
                    dork = prebuilt[int(sel)-1][1]
            except (EOFError, KeyboardInterrupt):
                continue
        
        elif choice == "10":
            prebuilt = [
                ('Admin login', 'inurl:admin inurl:login'),
                ('WordPress login', 'inurl:wp-login.php'),
                ('phpMyAdmin', 'inurl:phpmyadmin'),
                ('cPanel login', 'inurl:2082 | inurl:2083 | inurl:2086'),
                ('Webmail', 'inurl:webmail'),
                ('VPN login', 'inurl:vpn inurl:login'),
                ('Router login', 'intitle:"router" inurl:login'),
                ('FTP login', 'intitle:"index of" "ftp"'),
                ('SSH login', 'inurl:ssh inurl:login'),
                ('Citrix', 'inurl:citrix inurl:login'),
            ]
            print(f"\n  {Colors.NEON_GREEN}Login Page Dorks:{Colors.RESET}\n")
            for i, (name, d) in enumerate(prebuilt, 1):
                print(f"  {Colors.NEON_CYAN}[{i:2}]{Colors.RESET} {Colors.WHITE}{name}{Colors.RESET}")
                print(f"      {Colors.GRAY}{d}{Colors.RESET}")
            
            try:
                sel = input(f"\n  {Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} Select (1-{len(prebuilt)}): ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(prebuilt):
                    dork = prebuilt[int(sel)-1][1]
            except (EOFError, KeyboardInterrupt):
                continue
        
        elif choice == "11":
            prebuilt = [
                ('MongoDB exposed', 'intitle:"MongoDB" inurl:27017'),
                ('Elasticsearch', 'intitle:"elasticsearch" inurl:9200'),
                ('MySQL dumps', 'filetype:sql intext:"CREATE TABLE"'),
                ('PostgreSQL', 'inurl:5432 intext:postgres'),
                ('Redis', 'intitle:"redis" inurl:6379'),
                ('phpMyAdmin open', 'intitle:"phpMyAdmin" intext:"Welcome to phpMyAdmin"'),
                ('Adminer open', 'intitle:"Adminer" intext:"Login"'),
                ('Database backups', 'filetype:sql site:*.edu'),
                ('CouchDB', 'inurl:5984 intext:"couchdb"'),
                ('SQLite files', 'filetype:sqlite | filetype:db'),
            ]
            print(f"\n  {Colors.NEON_GREEN}Exposed Database Dorks:{Colors.RESET}\n")
            for i, (name, d) in enumerate(prebuilt, 1):
                print(f"  {Colors.NEON_CYAN}[{i:2}]{Colors.RESET} {Colors.WHITE}{name}{Colors.RESET}")
                print(f"      {Colors.GRAY}{d}{Colors.RESET}")
            
            try:
                sel = input(f"\n  {Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} Select (1-{len(prebuilt)}): ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(prebuilt):
                    dork = prebuilt[int(sel)-1][1]
            except (EOFError, KeyboardInterrupt):
                continue
        
        elif choice == "12":
            prebuilt = [
                ('wp-config.php', 'inurl:wp-config.php'),
                ('.htaccess', 'filetype:htaccess'),
                ('web.config', 'filetype:config inurl:web.config'),
                ('.env files', 'filetype:env'),
                ('nginx.conf', 'filetype:conf inurl:nginx'),
                ('apache conf', 'filetype:conf inurl:apache'),
                ('php.ini', 'filetype:ini inurl:php.ini'),
                ('settings.py', 'filetype:py inurl:settings'),
                ('application.yml', 'filetype:yml inurl:application'),
                ('docker-compose', 'filetype:yml inurl:docker-compose'),
            ]
            print(f"\n  {Colors.NEON_GREEN}Config File Dorks:{Colors.RESET}\n")
            for i, (name, d) in enumerate(prebuilt, 1):
                print(f"  {Colors.NEON_CYAN}[{i:2}]{Colors.RESET} {Colors.WHITE}{name}{Colors.RESET}")
                print(f"      {Colors.GRAY}{d}{Colors.RESET}")
            
            try:
                sel = input(f"\n  {Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} Select (1-{len(prebuilt)}): ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(prebuilt):
                    dork = prebuilt[int(sel)-1][1]
            except (EOFError, KeyboardInterrupt):
                continue
        
        elif choice == "13":
            prebuilt = [
                ('Directory listing', 'intitle:"index of /"'),
                ('Open FTP', 'intitle:"index of" inurl:ftp'),
                ('Apache default', 'intitle:"Apache2 Ubuntu Default Page"'),
                ('IIS default', 'intitle:"IIS Windows Server"'),
                ('Tomcat manager', 'inurl:manager/html intitle:tomcat'),
                ('JBoss console', 'inurl:jmx-console'),
                ('Jenkins open', 'intitle:"Dashboard [Jenkins]"'),
                ('GitLab exposed', 'inurl:gitlab intext:"sign in"'),
                ('Kibana open', 'intitle:"Kibana" inurl:app/kibana'),
                ('Grafana', 'intitle:"Grafana"'),
            ]
            print(f"\n  {Colors.NEON_GREEN}Vulnerable Server Dorks:{Colors.RESET}\n")
            for i, (name, d) in enumerate(prebuilt, 1):
                print(f"  {Colors.NEON_CYAN}[{i:2}]{Colors.RESET} {Colors.WHITE}{name}{Colors.RESET}")
                print(f"      {Colors.GRAY}{d}{Colors.RESET}")
            
            try:
                sel = input(f"\n  {Colors.NEON_MAGENTA}{Symbols.ARROW_RIGHT}{Colors.RESET} Select (1-{len(prebuilt)}): ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(prebuilt):
                    dork = prebuilt[int(sel)-1][1]
            except (EOFError, KeyboardInterrupt):
                continue
        
        elif choice == "14":
            print(f"\n  {Colors.NEON_GREEN}Custom Dork Builder{Colors.RESET}")
            print(f"  {Colors.GRAY}Combine operators. Leave blank to skip.{Colors.RESET}\n")
            
            parts = []
            try:
                site = input(f"  {Colors.ELECTRIC_BLUE}site:{Colors.RESET} ").strip()
                if site: parts.append(f"site:{site}")
                
                inurl = input(f"  {Colors.ELECTRIC_BLUE}inurl:{Colors.RESET} ").strip()
                if inurl: parts.append(f"inurl:{inurl}")
                
                intitle = input(f"  {Colors.ELECTRIC_BLUE}intitle:{Colors.RESET} ").strip()
                if intitle: parts.append(f'intitle:"{intitle}"')
                
                intext = input(f"  {Colors.ELECTRIC_BLUE}intext:{Colors.RESET} ").strip()
                if intext: parts.append(f'intext:"{intext}"')
                
                filetype = input(f"  {Colors.ELECTRIC_BLUE}filetype:{Colors.RESET} ").strip()
                if filetype: parts.append(f"filetype:{filetype}")
                
                extra = input(f"  {Colors.ELECTRIC_BLUE}Extra keywords:{Colors.RESET} ").strip()
                if extra: parts.append(extra)
            except (EOFError, KeyboardInterrupt):
                continue
            
            dork = " ".join(parts)
        
        if dork:
            encoded = urllib.parse.quote(dork)
            google_url = f"https://www.google.com/search?q={encoded}"
            
            print(f"\n  {Colors.NEON_MAGENTA}{'─' * 60}{Colors.RESET}")
            print(f"\n  {Colors.NEON_GREEN}{Symbols.CHECK} Generated Dork:{Colors.RESET}")
            print(f"\n  {Colors.WHITE}{dork}{Colors.RESET}")
            print(f"\n  {Colors.ELECTRIC_BLUE}Google URL:{Colors.RESET}")
            print(f"  {Colors.GRAY}{google_url}{Colors.RESET}")
            print(f"\n  {Colors.NEON_MAGENTA}{'─' * 60}{Colors.RESET}\n")
            
            try:
                copy = input(f"  {Colors.NEON_CYAN}Open in browser? [y/N]:{Colors.RESET} ").strip().lower()
                if copy == 'y':
                    import webbrowser
                    webbrowser.open(google_url)
            except (EOFError, KeyboardInterrupt):
                pass
        
        print()
    
    print(f"\n{Colors.NEON_MAGENTA}{'═' * 70}{Colors.RESET}\n")

