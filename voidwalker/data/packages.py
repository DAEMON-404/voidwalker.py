"""Package-manager install lists (apt / brew / pipx / uv / go / cargo / gem)."""

APT_TOOLS = [
    # Reconnaissance & Scanning - HTB Dante essentials
    # Note: For UDP scanning, use unicornscan, hping3, or nmap -sU
    "nmap", "masscan", "zmap", "unicornscan", "netdiscover", "arp-scan",
    "amass", "subfinder", "assetfinder", "dnsrecon", "dnsenum", "fierce",
    "whois", "host", "dig", "traceroute", "hping3", "fping",
    # Web Application Testing
    "gobuster", "feroxbuster", "dirb", "dirbuster", "nikto", "whatweb",
    "wpscan", "wfuzz", "sqlmap", "commix", "xsser", "cadaver",
    "davtest", "curl", "wget", "httpie", "lynx",
    # Password Attacks
    "hydra", "medusa", "john", "hashcat", "hashid", "hash-identifier",
    "crunch", "cewl", "wordlists", "seclists", "patator",
    # Wireless
    # (wifite omitted — its apt package wedges the unattended install; use the
    #  maintained wifite2 repo in TOOL_CATEGORIES["Wireless Tools"] instead)
    "aircrack-ng", "reaver", "bully", "pixiewps", "kismet",
    "mdk3", "mdk4", "macchanger", "iw", "wireless-tools",
    # Wireless - modern WPA/PMKID capture + cracking pipeline
    "hcxtools", "hcxdumptool", "cowpatty", "pyrit",
    # Wireless - rogue AP / WPA-Enterprise (evil twin, EAP cred harvest)
    "hostapd", "hostapd-wpe", "freeradius", "dnsmasq", "wpasupplicant",
    # Wireless - radio management helper (unblock rfkill-soft-blocked adapters)
    "rfkill",
    # Wireless - injection/monitor-mode driver for RTL8812AU adapters
    # (Alfa AWUS036ACH etc.) — the aircrack-ng suite needs this to inject
    "realtek-rtl88xxau-dkms",
    # Exploitation
    "metasploit-framework", "exploitdb", "searchsploit",
    "shellnoob", "veil", "msfpc",
    # Sniffing & Spoofing
    "wireshark", "tshark", "tcpdump", "ettercap-common", "ettercap-text-only",
    "bettercap", "dsniff", "macof", "arpspoof", "responder",
    # Post-Exploitation
    "enum4linux-ng", "enum4linux", "smbclient", "smbmap", "rpcclient", "nbtscan",
    "onesixtyone", "snmpwalk", "snmp", "redis-tools",
    "ldap-utils", "nfs-common", "rpcbind", "krb5-user",
    # Pivoting & Tunneling
    "proxychains4", "sshuttle", "socat", "stunnel4", "redsocks",
    "chisel", "netcat-traditional", "ncat", "cryptcat",
    # Forensics & Recovery
    "binwalk", "foremost", "exiftool", "steghide", "stegcracker",
    "volatility3", "autopsy", "sleuthkit", "testdisk", "photorec",
    "bulk-extractor", "scalpel", "dc3dd",
    # Utilities
    "zsh", "rlwrap", "tmux", "screen", "vim", "nano", "jq", "yq",
    "tree", "htop", "ncdu", "lsof", "strace", "ltrace",
    "gdb", "radare2", "ghidra",
    # Development & Build - HTB Dante essentials
    "golang-go", "rustc", "cargo", "python3-pip", "pipx", "python3-venv",
    "ruby", "ruby-dev", "ruby-bundler", "nodejs", "npm",
    "build-essential", "cmake", "make", "gcc", "g++",
    "git", "git-lfs", "p7zip-full", "unzip", "zip",
    "libssl-dev", "libffi-dev", "libpcap-dev",
    "apt-transport-https", "ca-certificates", "gnupg", "lsb-release",
    "e2fsprogs", "dnsutils", "ssh",
    # Networking
    "openvpn", "wireguard", "iproute2", "net-tools", "bridge-utils",
    "iptables", "nftables", "ufw",
]


BREW_TOOLS = [
    # Reconnaissance & Scanning
    "nmap", "masscan", "amass", "subfinder", "dnsrecon", "dnsenum",
    "whois", "fping",
    # Web Application Testing
    "gobuster", "feroxbuster", "nikto", "whatweb",
    "sqlmap", "curl", "wget", "httpie",
    # Password Attacks
    "hydra", "john-jumbo", "hashcat", "crunch", "cewl",
    # Wireless (offline handshake/PMKID cracking only — monitor-mode
    # injection needs Linux drivers, so capture tools are omitted here)
    "aircrack-ng", "hcxtools", "cowpatty",
    # Sniffing & Spoofing
    "tcpdump", "bettercap",
    # Post-Exploitation
    "samba", "nbtscan", "openldap",
    # Pivoting & Tunneling
    "proxychains-ng", "socat", "ncat",
    # Utilities
    "rlwrap", "tmux", "screen", "vim", "jq", "yq",
    "tree", "htop", "ncdu",
    "radare2",
    # Development & Build
    "go", "rust", "python@3", "pipx", "ruby", "node", "npm",
    "cmake", "make",
    "git", "git-lfs", "p7zip", "unzip", "zip",
    "openssl", "libffi", "libpcap",
    # Networking
    "openvpn", "wireguard-tools",
]


BREW_CASKS = [
    "wireshark",
    "burp-suite",
    "bloodhound",
    "ghidra",
]


PIPX_TOOLS = [
    # Active Directory & Windows
    # NOTE: impacket, certipy-ad, bloodyAD, netexec are installed via UV (see UV_TOOLS)
    "bloodhound",
    "bloodhound-python",
    "bloodhound-ce-python",
    "ldapdomaindump",
    "coercer",
    "mitm6",
    "adidnsdump",
    "ldeep",
    "pypykatz",
    "pywerview",
    "dploot",
    "donpapi",
    "roadrecon",
    "pre2k",
    "kerbrute",
    "sprayhound",
    "crackmapexec",
    "evil-winrm",
    # Web & Recon
    "httpx",
    "nuclei",
    "subfinder",
    "waybackurls",
    "gau",
    "arjun",
    "photon",
    "dirsearch",
    "uro",
    "hakrawler",
    # Cloud & Infrastructure
    "awscli",
    "azure-cli",
    "cloudsplaining",
    "scoutsuite",
    "prowler",
    "pacu",
    # Exploitation & Post-Ex
    "pwntools",
    "ropgadget",
    "ropper",
    "pwncat-cs",
    "villain",
    "hoaxshell",
    # OSINT & Recon
    "theHarvester",
    "holehe",
    "socialscan",
    "maigret",
    "sherlock-project",
    "h8mail",
    # Password & Crypto
    "hashcrack",
    "name-that-hash",
    "stegcracker",
    # Misc Utilities
    "updog",
    "python-pptx",
    "xlrd",
    "oletools",
    "yara-python",
    # Added: pure-Python, architecture-independent
    "lsassy",
    "masky",
    "trevorspray",
    "minidump",
    "certsync",
]


GO_TOOLS = [
    ("rustscan", "https://github.com/RustScan/RustScan/releases/latest/download/rustscan_2.3.0_amd64.deb"),
    ("nuclei", "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"),
    ("httpx", "go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest"),
    ("subfinder", "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"),
    ("naabu", "go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"),
    ("dnsx", "go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest"),
    ("katana", "go install -v github.com/projectdiscovery/katana/cmd/katana@latest"),
    ("ffuf", "go install -v github.com/ffuf/ffuf/v2@latest"),
    ("gobuster", "go install -v github.com/OJ/gobuster/v3@latest"),
    ("gau", "go install -v github.com/lc/gau/v2/cmd/gau@latest"),
    ("hakrawler", "go install -v github.com/hakluke/hakrawler@latest"),
    ("waybackurls", "go install -v github.com/tomnomnom/waybackurls@latest"),
    ("assetfinder", "go install -v github.com/tomnomnom/assetfinder@latest"),
    ("httprobe", "go install -v github.com/tomnomnom/httprobe@latest"),
    ("anew", "go install -v github.com/tomnomnom/anew@latest"),
    ("qsreplace", "go install -v github.com/tomnomnom/qsreplace@latest"),
    ("dalfox", "go install -v github.com/hahwul/dalfox/v2@latest"),
    ("kxss", "go install -v github.com/Emoe/kxss@latest"),
    ("crlfuzz", "go install -v github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest"),
    ("interactsh-client", "go install -v github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest"),
    # Added: compiled via `go install`, so they build natively on any arch (x86_64/arm64/armv7)
    ("trufflehog", "go install -v github.com/trufflesecurity/trufflehog/v3@latest"),
    ("tlsx", "go install -v github.com/projectdiscovery/tlsx/cmd/tlsx@latest"),
    ("asnmap", "go install -v github.com/projectdiscovery/asnmap/cmd/asnmap@latest"),
    ("mapcidr", "go install -v github.com/projectdiscovery/mapcidr/cmd/mapcidr@latest"),
    ("uncover", "go install -v github.com/projectdiscovery/uncover/cmd/uncover@latest"),
    ("cdncheck", "go install -v github.com/projectdiscovery/cdncheck/cmd/cdncheck@latest"),
    ("shuffledns", "go install -v github.com/projectdiscovery/shuffledns/cmd/shuffledns@latest"),
]


CARGO_TOOLS = [
    "rustscan",
    "feroxbuster",
    "ripgrep",
    "fd-find",
    "bat",
    "exa",
    "hyperfine",
]


GEM_TOOLS = [
    # Ruby-based Penetration Testing Tools
    "wpscan",      # WordPress security scanner
    "evil-winrm",  # Windows Remote Management (WinRM) shell
]


UV_TOOLS = [
    "impacket",
    "bloodyad",
    "certipy-ad",
    "netexec",
    "bofhound",  # turn netexec/ldapsearch logs into BloodHound-CE ingest JSON
]

