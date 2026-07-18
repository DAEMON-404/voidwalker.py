"""Architecture-aware binary catalog.

Two dictionaries live here:

* :data:`CROSS_PLATFORM_TOOLS` — standalone binaries fetched for *every*
  ``(os, arch)`` they ship for, so the operator has something to drop on
  whatever target (or attack box) they end up on, regardless of CPU.
* :data:`SPECIAL_TOOLS` — single host-installed binaries (placed on ``PATH``)
  where only the build matching the *current* host architecture is fetched.

Schema for every entry::

    "tool": {
        "description": str,
        "dest_dir":   "tools/...",          # relative to ~/voidwalker
        "transfer":   True,                  # arsenal binary -> fetch all variants
        "assets": {
            (os, arch): [(filename, url), ...],
            ...
        },
    }

``os``   is one of ``windows`` / ``linux`` / ``darwin``.
``arch`` is one of ``amd64`` / ``arm64`` / ``armv7`` / ``386`` (see hostinfo.py).

When upstream does not publish a build for a given ``(os, arch)`` the key is
simply omitted; :func:`voidwalker.hostinfo.select_asset` and the installer skip
it cleanly instead of fetching a binary that cannot run.
"""

# ── Standalone cross-platform binaries (download all published variants) ─────
CROSS_PLATFORM_TOOLS = {
    "chisel": {
        "description": "TCP/UDP tunnelling over HTTP",
        "dest_dir": "tools/pivoting/chisel",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("chisel_windows_amd64.exe", "https://github.com/jpillora/chisel/releases/download/v1.10.1/chisel_1.10.1_windows_amd64.gz")],
            ("windows", "arm64"): [("chisel_windows_arm64.exe", "https://github.com/jpillora/chisel/releases/download/v1.10.1/chisel_1.10.1_windows_arm64.gz")],
            ("linux", "amd64"): [("chisel_linux_amd64", "https://github.com/jpillora/chisel/releases/download/v1.10.1/chisel_1.10.1_linux_amd64.gz")],
            ("linux", "arm64"): [("chisel_linux_arm64", "https://github.com/jpillora/chisel/releases/download/v1.10.1/chisel_1.10.1_linux_arm64.gz")],
            ("linux", "armv7"): [("chisel_linux_armv7", "https://github.com/jpillora/chisel/releases/download/v1.10.1/chisel_1.10.1_linux_armv7.gz")],
            ("darwin", "amd64"): [("chisel_darwin_amd64", "https://github.com/jpillora/chisel/releases/download/v1.10.1/chisel_1.10.1_darwin_amd64.gz")],
            ("darwin", "arm64"): [("chisel_darwin_arm64", "https://github.com/jpillora/chisel/releases/download/v1.10.1/chisel_1.10.1_darwin_arm64.gz")],
        },
    },
    "ligolo-ng": {
        "description": "Tunnelling/pivoting tool using TUN interfaces",
        "dest_dir": "tools/pivoting/ligolo-ng",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("ligolo-ng_agent_windows_amd64.zip", "https://github.com/nicocha30/ligolo-ng/releases/download/v0.7.5/ligolo-ng_agent_0.7.5_windows_amd64.zip")],
            ("windows", "arm64"): [("ligolo-ng_agent_windows_arm64.zip", "https://github.com/nicocha30/ligolo-ng/releases/download/v0.7.5/ligolo-ng_agent_0.7.5_windows_arm64.zip")],
            ("linux", "amd64"): [
                ("ligolo-ng_proxy_linux_amd64.tar.gz", "https://github.com/nicocha30/ligolo-ng/releases/download/v0.7.5/ligolo-ng_proxy_0.7.5_linux_amd64.tar.gz"),
                ("ligolo-ng_agent_linux_amd64.tar.gz", "https://github.com/nicocha30/ligolo-ng/releases/download/v0.7.5/ligolo-ng_agent_0.7.5_linux_amd64.tar.gz"),
            ],
            ("linux", "arm64"): [
                ("ligolo-ng_proxy_linux_arm64.tar.gz", "https://github.com/nicocha30/ligolo-ng/releases/download/v0.7.5/ligolo-ng_proxy_0.7.5_linux_arm64.tar.gz"),
                ("ligolo-ng_agent_linux_arm64.tar.gz", "https://github.com/nicocha30/ligolo-ng/releases/download/v0.7.5/ligolo-ng_agent_0.7.5_linux_arm64.tar.gz"),
            ],
            ("linux", "armv7"): [
                ("ligolo-ng_agent_linux_armv7.tar.gz", "https://github.com/nicocha30/ligolo-ng/releases/download/v0.7.5/ligolo-ng_agent_0.7.5_linux_armv7.tar.gz"),
            ],
            ("darwin", "amd64"): [
                ("ligolo-ng_proxy_darwin_amd64.tar.gz", "https://github.com/nicocha30/ligolo-ng/releases/download/v0.7.5/ligolo-ng_proxy_0.7.5_darwin_amd64.tar.gz"),
                ("ligolo-ng_agent_darwin_amd64.tar.gz", "https://github.com/nicocha30/ligolo-ng/releases/download/v0.7.5/ligolo-ng_agent_0.7.5_darwin_amd64.tar.gz"),
            ],
            ("darwin", "arm64"): [
                ("ligolo-ng_proxy_darwin_arm64.tar.gz", "https://github.com/nicocha30/ligolo-ng/releases/download/v0.7.5/ligolo-ng_proxy_0.7.5_darwin_arm64.tar.gz"),
                ("ligolo-ng_agent_darwin_arm64.tar.gz", "https://github.com/nicocha30/ligolo-ng/releases/download/v0.7.5/ligolo-ng_agent_0.7.5_darwin_arm64.tar.gz"),
            ],
        },
    },
    "fscan": {
        "description": "Internal network scanner (shadow1ng)",
        "dest_dir_win": "tools/windows/scanning",
        "dest_dir_linux": "tools/linux/scanning",
        "dest_dir": "tools/scanning/fscan",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("fscan64.exe", "https://github.com/shadow1ng/fscan/releases/latest/download/fscan64.exe")],
            ("windows", "386"): [("fscan32.exe", "https://github.com/shadow1ng/fscan/releases/latest/download/fscan32.exe")],
            ("linux", "amd64"): [("fscan_amd64", "https://github.com/shadow1ng/fscan/releases/latest/download/fscan")],
            ("linux", "386"): [("fscan_386", "https://github.com/shadow1ng/fscan/releases/latest/download/fscan32")],
            ("linux", "arm64"): [("fscan_arm64", "https://github.com/shadow1ng/fscan/releases/latest/download/fscan_arm64")],
        },
    },
    "kerbrute": {
        "description": "Kerberos brute-force / user enumeration",
        "dest_dir": "tools/ad/kerbrute",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("kerbrute_windows_amd64.exe", "https://github.com/ropnop/kerbrute/releases/latest/download/kerbrute_windows_amd64.exe")],
            ("linux", "amd64"): [("kerbrute_linux_amd64", "https://github.com/ropnop/kerbrute/releases/latest/download/kerbrute_linux_amd64")],
            ("linux", "arm64"): [("kerbrute_linux_arm64", "https://github.com/ropnop/kerbrute/releases/latest/download/kerbrute_linux_arm64")],
            ("darwin", "amd64"): [("kerbrute_darwin_amd64", "https://github.com/ropnop/kerbrute/releases/latest/download/kerbrute_darwin_amd64")],
            ("darwin", "arm64"): [("kerbrute_darwin_arm64", "https://github.com/ropnop/kerbrute/releases/latest/download/kerbrute_darwin_arm64")],
        },
    },
    "sliver": {
        "description": "Sliver C2 — adversary emulation framework",
        "dest_dir": "tools/c2/sliver",
        "transfer": True,
        "assets": {
            ("linux", "amd64"): [
                ("sliver-server_linux", "https://github.com/BishopFox/sliver/releases/latest/download/sliver-server_linux"),
                ("sliver-client_linux", "https://github.com/BishopFox/sliver/releases/latest/download/sliver-client_linux"),
            ],
            ("linux", "arm64"): [
                ("sliver-server_linux-arm64", "https://github.com/BishopFox/sliver/releases/latest/download/sliver-server_linux-arm64"),
                ("sliver-client_linux-arm64", "https://github.com/BishopFox/sliver/releases/latest/download/sliver-client_linux-arm64"),
            ],
            ("darwin", "amd64"): [("sliver-client_macos", "https://github.com/BishopFox/sliver/releases/latest/download/sliver-client_macos")],
            ("darwin", "arm64"): [("sliver-client_macos-arm64", "https://github.com/BishopFox/sliver/releases/latest/download/sliver-client_macos-arm64")],
            ("windows", "amd64"): [("sliver-client_windows.exe", "https://github.com/BishopFox/sliver/releases/latest/download/sliver-client_windows.exe")],
        },
    },
    "pspy": {
        "description": "Linux process snooper (unprivileged)",
        "dest_dir": "tools/linux/enum",
        "transfer": True,
        "assets": {
            ("linux", "amd64"): [
                ("pspy64", "https://github.com/DominicBreuker/pspy/releases/latest/download/pspy64"),
                ("pspy64s", "https://github.com/DominicBreuker/pspy/releases/latest/download/pspy64s"),
            ],
            ("linux", "386"): [
                ("pspy32", "https://github.com/DominicBreuker/pspy/releases/latest/download/pspy32"),
                ("pspy32s", "https://github.com/DominicBreuker/pspy/releases/latest/download/pspy32s"),
            ],
            ("linux", "arm64"): [("pspy64arm", "https://github.com/DominicBreuker/pspy/releases/latest/download/pspy64arm")],
            ("linux", "armv7"): [("pspy32arm", "https://github.com/DominicBreuker/pspy/releases/latest/download/pspy32arm")],
        },
    },
    "winpeas": {
        "description": "Windows privilege escalation scanner",
        "dest_dir": "tools/windows/privesc",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [
                ("winPEASx64.exe", "https://github.com/carlospolop/PEASS-ng/releases/latest/download/winPEASx64.exe"),
                ("winPEASany.exe", "https://github.com/carlospolop/PEASS-ng/releases/latest/download/winPEASany.exe"),
                ("winPEAS.bat", "https://github.com/carlospolop/PEASS-ng/releases/latest/download/winPEAS.bat"),
            ],
            ("windows", "386"): [("winPEASx86.exe", "https://github.com/carlospolop/PEASS-ng/releases/latest/download/winPEASx86.exe")],
        },
    },
    "linpeas": {
        "description": "Linux privilege escalation scanner",
        "dest_dir": "tools/linux/privesc",
        "transfer": True,
        "assets": {
            # linpeas.sh is arch-independent; fetch it for every Linux arch.
            ("linux", "amd64"): [
                ("linpeas.sh", "https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh"),
                ("linpeas_linux_amd64", "https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas_linux_amd64"),
            ],
            ("linux", "386"): [("linpeas_linux_386", "https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas_linux_386")],
            ("linux", "arm64"): [
                ("linpeas.sh", "https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh"),
                ("linpeas_linux_arm64", "https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas_linux_arm64"),
            ],
            ("linux", "armv7"): [("linpeas.sh", "https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh")],
        },
    },
    "stowaway": {
        "description": "Multi-hop proxy tool for pentesters",
        "dest_dir": "tools/pivoting/stowaway",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [
                ("windows_x64_admin.exe", "https://github.com/ph4ntonn/Stowaway/releases/latest/download/windows_x64_admin.exe"),
                ("windows_x64_agent.exe", "https://github.com/ph4ntonn/Stowaway/releases/latest/download/windows_x64_agent.exe"),
            ],
            ("linux", "amd64"): [
                ("linux_x64_admin", "https://github.com/ph4ntonn/Stowaway/releases/latest/download/linux_x64_admin"),
                ("linux_x64_agent", "https://github.com/ph4ntonn/Stowaway/releases/latest/download/linux_x64_agent"),
            ],
            ("linux", "arm64"): [
                ("linux_arm64_admin", "https://github.com/ph4ntonn/Stowaway/releases/latest/download/linux_arm64_admin"),
                ("linux_arm64_agent", "https://github.com/ph4ntonn/Stowaway/releases/latest/download/linux_arm64_agent"),
            ],
            ("darwin", "amd64"): [
                ("macos_admin", "https://github.com/ph4ntonn/Stowaway/releases/latest/download/macos_admin"),
                ("macos_agent", "https://github.com/ph4ntonn/Stowaway/releases/latest/download/macos_agent"),
            ],
        },
    },
    "frp": {
        "description": "Fast reverse proxy — expose local servers",
        "dest_dir": "tools/pivoting/frp",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("frp_windows_amd64.zip", "https://github.com/fatedier/frp/releases/latest/download/frp_0.61.1_windows_amd64.zip")],
            ("windows", "arm64"): [("frp_windows_arm64.zip", "https://github.com/fatedier/frp/releases/latest/download/frp_0.61.1_windows_arm64.zip")],
            ("linux", "amd64"): [("frp_linux_amd64.tar.gz", "https://github.com/fatedier/frp/releases/latest/download/frp_0.61.1_linux_amd64.tar.gz")],
            ("linux", "arm64"): [("frp_linux_arm64.tar.gz", "https://github.com/fatedier/frp/releases/latest/download/frp_0.61.1_linux_arm64.tar.gz")],
            ("linux", "armv7"): [("frp_linux_arm.tar.gz", "https://github.com/fatedier/frp/releases/latest/download/frp_0.61.1_linux_arm.tar.gz")],
            ("darwin", "amd64"): [("frp_darwin_amd64.tar.gz", "https://github.com/fatedier/frp/releases/latest/download/frp_0.61.1_darwin_amd64.tar.gz")],
            ("darwin", "arm64"): [("frp_darwin_arm64.tar.gz", "https://github.com/fatedier/frp/releases/latest/download/frp_0.61.1_darwin_arm64.tar.gz")],
        },
    },
    "gost": {
        "description": "GO Simple Tunnel — encrypted proxy chains",
        "dest_dir": "tools/pivoting/gost",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("gost_windows_amd64.zip", "https://github.com/ginuerzh/gost/releases/latest/download/gost-windows-amd64-2.12.0.zip")],
            ("linux", "amd64"): [("gost_linux_amd64.gz", "https://github.com/ginuerzh/gost/releases/latest/download/gost-linux-amd64-2.12.0.gz")],
            ("linux", "arm64"): [("gost_linux_arm64.gz", "https://github.com/ginuerzh/gost/releases/latest/download/gost-linux-armv8-2.12.0.gz")],
            ("linux", "armv7"): [("gost_linux_armv7.gz", "https://github.com/ginuerzh/gost/releases/latest/download/gost-linux-armv7-2.12.0.gz")],
            ("darwin", "amd64"): [("gost_darwin_amd64.gz", "https://github.com/ginuerzh/gost/releases/latest/download/gost-darwin-amd64-2.12.0.gz")],
        },
    },
    "netcat-static": {
        "description": "Static netcat binaries for file transfer",
        "dest_dir": "tools/pivoting/netcat",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [
                ("nc64.exe", "https://github.com/int0x33/nc.exe/raw/master/nc64.exe"),
                ("nc.exe", "https://github.com/int0x33/nc.exe/raw/master/nc.exe"),
            ],
            ("linux", "amd64"): [("ncat_static", "https://github.com/andrew-d/static-binaries/raw/master/binaries/linux/x86_64/ncat")],
            ("linux", "arm64"): [("ncat_static_arm64", "https://github.com/andrew-d/static-binaries/raw/master/binaries/linux/arm64/ncat")],
            ("linux", "armv7"): [("ncat_static_armv7", "https://github.com/andrew-d/static-binaries/raw/master/binaries/linux/armv7l/ncat")],
        },
    },
    "socat-static": {
        "description": "Static socat binary for Linux targets",
        "dest_dir": "tools/pivoting/socat",
        "transfer": True,
        "assets": {
            ("linux", "amd64"): [("socat_static", "https://github.com/andrew-d/static-binaries/raw/master/binaries/linux/x86_64/socat")],
            ("linux", "arm64"): [("socat_static_arm64", "https://github.com/andrew-d/static-binaries/raw/master/binaries/linux/arm64/socat")],
            ("linux", "armv7"): [("socat_static_armv7", "https://github.com/andrew-d/static-binaries/raw/master/binaries/linux/armv7l/socat")],
        },
    },
    "mimikatz": {
        "description": "Windows credential dumping — Mimikatz trunk",
        "dest_dir": "tools/windows/creds",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("mimikatz_trunk.zip", "https://github.com/gentilkiwi/mimikatz/releases/latest/download/mimikatz_trunk.zip")],
        },
    },
    "lazagne": {
        "description": "Multi-platform credential recovery",
        "dest_dir": "tools/creds/lazagne",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("LaZagne.exe", "https://github.com/AlessandroZ/LaZagne/releases/latest/download/LaZagne.exe")],
        },
    },
    "godpotato": {
        "description": "Potato privilege escalation (.NET)",
        "dest_dir": "tools/windows/privesc",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [
                ("GodPotato-NET2.exe", "https://github.com/BeichenDream/GodPotato/releases/latest/download/GodPotato-NET2.exe"),
                ("GodPotato-NET4.exe", "https://github.com/BeichenDream/GodPotato/releases/latest/download/GodPotato-NET4.exe"),
                ("GodPotato-NET35.exe", "https://github.com/BeichenDream/GodPotato/releases/latest/download/GodPotato-NET35.exe"),
            ],
        },
    },
    "printspoofer": {
        "description": "Pipe privilege escalation",
        "dest_dir": "tools/windows/privesc",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("PrintSpoofer64.exe", "https://github.com/itm4n/PrintSpoofer/releases/latest/download/PrintSpoofer64.exe")],
            ("windows", "386"): [("PrintSpoofer32.exe", "https://github.com/itm4n/PrintSpoofer/releases/latest/download/PrintSpoofer32.exe")],
        },
    },
    "rustscan": {
        "description": "Fast port scanner written in Rust",
        "dest_dir": "tools/scanning/rustscan",
        # host-native: only fetch the build matching this machine
        "assets": {
            ("linux", "amd64"): [("rustscan_amd64.deb", "https://github.com/RustScan/RustScan/releases/latest/download/rustscan_2.3.0_amd64.deb")],
            ("linux", "arm64"): [("rustscan_arm64.deb", "https://github.com/RustScan/RustScan/releases/latest/download/rustscan_2.3.0_arm64.deb")],
            ("darwin", "arm64"): [("rustscan_macos_arm64", "https://github.com/RustScan/RustScan/releases/latest/download/rustscan_2.3.0_aarch64-apple-darwin")],
            ("darwin", "amd64"): [("rustscan_macos_amd64", "https://github.com/RustScan/RustScan/releases/latest/download/rustscan_2.3.0_x86_64-apple-darwin")],
        },
    },
    "bloodhound-collectors": {
        "description": "BloodHound data collection — SharpHound",
        "dest_dir": "tools/ad/bloodhound",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [
                ("SharpHound.exe", "https://github.com/BloodHoundAD/SharpHound/releases/latest/download/SharpHound.exe"),
                ("SharpHound.ps1", "https://github.com/BloodHoundAD/SharpHound/releases/latest/download/SharpHound.ps1"),
            ],
        },
    },
    "rubeus": {
        "description": "Kerberos abuse toolkit (C#)",
        "dest_dir": "tools/windows/kerberos",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("Rubeus.exe", "https://github.com/r3motecontrol/Ghostpack-CompiledBinaries/raw/master/Rubeus.exe")],
        },
    },
    "juicypotatong": {
        "description": "JuicyPotatoNG — next-gen potato priv-esc",
        "dest_dir": "tools/windows/privesc",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("JuicyPotatoNG.zip", "https://github.com/antonioCoco/JuicyPotatoNG/releases/latest/download/JuicyPotatoNG.zip")],
        },
    },
    "runascs": {
        "description": "RunAs alternative with credentials",
        "dest_dir": "tools/windows/misc",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("RunasCs.zip", "https://github.com/antonioCoco/RunasCs/releases/latest/download/RunasCs.zip")],
        },
    },
    "nanodump": {
        "description": "Stealthy LSASS process dumper",
        "dest_dir": "tools/windows/creds",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("nanodump.x64.exe", "https://github.com/fortra/nanodump/releases/latest/download/nanodump.x64.exe")],
            ("windows", "386"): [("nanodump.x86.exe", "https://github.com/fortra/nanodump/releases/latest/download/nanodump.x86.exe")],
        },
    },
    "snaffler": {
        "description": "Credential hunting across file shares",
        "dest_dir": "tools/windows/enum",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("Snaffler.exe", "https://github.com/SnaffCon/Snaffler/releases/latest/download/Snaffler.exe")],
        },
    },
    "inveigh": {
        "description": "LLMNR/NBNS/mDNS poisoning tool",
        "dest_dir": "tools/windows/inveigh",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("Inveigh.exe", "https://github.com/Kevin-Robertson/Inveigh/releases/latest/download/Inveigh.exe")],
        },
    },
    "krbrelayup": {
        "description": "Kerberos relay privilege escalation",
        "dest_dir": "tools/windows/kerberos",
        "transfer": True,
        "assets": {
            ("windows", "amd64"): [("KrbRelayUp.exe", "https://github.com/Dec0ne/KrbRelayUp/releases/latest/download/KrbRelayUp.exe")],
        },
    },

    # ── New cross-platform tooling (arch-aware) ──────────────────────────────
    "gitleaks": {
        "description": "Secret scanner for git repos & files",
        "dest_dir": "tools/web/scanners/gitleaks",
        "transfer": True,
        "assets": {
            ("linux", "amd64"): [("gitleaks_linux_x64.tar.gz", "https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.4_linux_x64.tar.gz")],
            ("linux", "arm64"): [("gitleaks_linux_arm64.tar.gz", "https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.4_linux_arm64.tar.gz")],
            ("linux", "armv7"): [("gitleaks_linux_armv7.tar.gz", "https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.4_linux_armv7.tar.gz")],
            ("darwin", "amd64"): [("gitleaks_darwin_x64.tar.gz", "https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.4_darwin_x64.tar.gz")],
            ("darwin", "arm64"): [("gitleaks_darwin_arm64.tar.gz", "https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.4_darwin_arm64.tar.gz")],
            ("windows", "amd64"): [("gitleaks_windows_x64.zip", "https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.4_windows_x64.zip")],
        },
    },
    "trivy": {
        "description": "Container / IaC / filesystem vulnerability scanner",
        "dest_dir": "tools/container/scanners/trivy",
        "transfer": True,
        "assets": {
            ("linux", "amd64"): [("trivy_Linux-64bit.tar.gz", "https://github.com/aquasecurity/trivy/releases/latest/download/trivy_0.53.0_Linux-64bit.tar.gz")],
            ("linux", "arm64"): [("trivy_Linux-ARM64.tar.gz", "https://github.com/aquasecurity/trivy/releases/latest/download/trivy_0.53.0_Linux-ARM64.tar.gz")],
            ("darwin", "amd64"): [("trivy_macOS-64bit.tar.gz", "https://github.com/aquasecurity/trivy/releases/latest/download/trivy_0.53.0_macOS-64bit.tar.gz")],
            ("darwin", "arm64"): [("trivy_macOS-ARM64.tar.gz", "https://github.com/aquasecurity/trivy/releases/latest/download/trivy_0.53.0_macOS-ARM64.tar.gz")],
        },
    },
    "cloudfox": {
        "description": "Cloud attack-surface enumeration (AWS/Azure/GCP)",
        "dest_dir": "tools/cloud/cloudfox",
        "transfer": True,
        "assets": {
            ("linux", "amd64"): [("cloudfox-linux-amd64.zip", "https://github.com/BishopFox/cloudfox/releases/latest/download/cloudfox-linux-amd64.zip")],
            ("linux", "arm64"): [("cloudfox-linux-arm64.zip", "https://github.com/BishopFox/cloudfox/releases/latest/download/cloudfox-linux-arm64.zip")],
            ("darwin", "amd64"): [("cloudfox-macos-amd64.zip", "https://github.com/BishopFox/cloudfox/releases/latest/download/cloudfox-macos-amd64.zip")],
            ("darwin", "arm64"): [("cloudfox-macos-arm64.zip", "https://github.com/BishopFox/cloudfox/releases/latest/download/cloudfox-macos-arm64.zip")],
            ("windows", "amd64"): [("cloudfox-windows-amd64.zip", "https://github.com/BishopFox/cloudfox/releases/latest/download/cloudfox-windows-amd64.zip")],
        },
    },
    "gowitness": {
        "description": "Web screenshot / recon utility",
        "dest_dir": "tools/web/scanners/gowitness",
        "transfer": True,
        "assets": {
            ("linux", "amd64"): [("gowitness-linux-amd64", "https://github.com/sensepost/gowitness/releases/latest/download/gowitness-linux-amd64")],
            ("linux", "arm64"): [("gowitness-linux-arm64", "https://github.com/sensepost/gowitness/releases/latest/download/gowitness-linux-arm64")],
            ("darwin", "arm64"): [("gowitness-darwin-arm64", "https://github.com/sensepost/gowitness/releases/latest/download/gowitness-darwin-arm64")],
            ("windows", "amd64"): [("gowitness-windows-amd64.exe", "https://github.com/sensepost/gowitness/releases/latest/download/gowitness-windows-amd64.exe")],
        },
    },
}

# ── Host-installed binaries (only the current-arch build is fetched) ─────────
# Each entry is placed on PATH (default /usr/local/bin) for the current host.
SPECIAL_TOOLS = {
    "kerbrute": {
        "type": "binary",
        "dest": "/usr/local/bin/kerbrute",
        "chmod": True,
        "assets": {
            ("linux", "amd64"): [("kerbrute", "https://github.com/ropnop/kerbrute/releases/latest/download/kerbrute_linux_amd64")],
            ("linux", "arm64"): [("kerbrute", "https://github.com/ropnop/kerbrute/releases/latest/download/kerbrute_linux_arm64")],
            ("darwin", "amd64"): [("kerbrute", "https://github.com/ropnop/kerbrute/releases/latest/download/kerbrute_darwin_amd64")],
            ("darwin", "arm64"): [("kerbrute", "https://github.com/ropnop/kerbrute/releases/latest/download/kerbrute_darwin_arm64")],
        },
    },
}
