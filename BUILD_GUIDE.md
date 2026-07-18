# VoidWalker — C# Build Guide

> Build offensive C# tools from source for maximum OPSEC.  
> Pre-compiled binaries are heavily signatured by AV/EDR — building from source lets you customise, obfuscate, and evade detection.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Automated Building (VoidWalker)](#automated-building-voidwalker)
3. [Manual Building — dotnet CLI](#manual-building--dotnet-cli)
4. [Manual Building — Visual Studio](#manual-building--visual-studio)
5. [Cross-Compilation (Linux/macOS → Windows)](#cross-compilation-linuxmacos--windows)
6. [OPSEC Considerations](#opsec-considerations)
7. [Troubleshooting](#troubleshooting)
8. [Tool Reference](#tool-reference)

---

## Prerequisites

### .NET SDK Installation

**macOS (Homebrew):**
```bash
brew install dotnet-sdk
```

**Linux (Ubuntu/Debian):**
```bash
# Option 1: Microsoft packages
wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
sudo apt-get update && sudo apt-get install -y dotnet-sdk-8.0

# Option 2: Install script
wget https://dot.net/v1/dotnet-install.sh
bash dotnet-install.sh --channel 8.0
export PATH="$HOME/.dotnet:$PATH"
```

**Windows:**
- Download from [https://dotnet.microsoft.com/download](https://dotnet.microsoft.com/download)
- Or use `winget install Microsoft.DotNet.SDK.8`

**Verify installation:**
```bash
dotnet --version
# Should output 8.x.x or similar
```

### ARM64 / aarch64 hosts (Apple Silicon, Raspberry Pi, Graviton)

The `dotnet-install.sh` script auto-detects your CPU and pulls the correct SDK,
so the Linux **Option 2** above works unchanged on arm64. On Apple Silicon,
`brew install dotnet-sdk` installs the native arm64 SDK.

Note on output: the GhostPack-style targets here build **AnyCPU / IL** assemblies
(`net462`), so the produced `.exe` runs on Windows regardless of the *build host's*
CPU — you can compile them on an ARM Linux/macOS box and still get a working
Windows binary. You only need an explicit RID (`-r win-x64` / `-r win-arm64`) when
producing self-contained, single-file builds for a specific Windows architecture.

### Additional Requirements

- **Git** — for cloning source repositories
- **NuGet** — included with .NET SDK (used for package restore)
- **Mono** (optional, Linux/macOS) — for building .NET Framework 4.x targets

---

## Automated Building (VoidWalker)

VoidWalker can automatically clone, build, and collect 21 C# tools:

```bash
# Run VoidWalker and select option 6: "Build C# Tools from Source"
sudo python3 voidwalker.py

# Or use it programmatically:
# The script will:
# 1. Check for dotnet SDK
# 2. Clone each repo to ~/voidwalker/tools/build-src/<ToolName>/
# 3. Run: dotnet restore && dotnet build -c Release
# 4. Copy compiled .exe files to ~/voidwalker/tools/windows/compiled/<ToolName>/
```

### What gets built:

| Tool | Description | Framework |
|------|-------------|-----------|
| Rubeus | Kerberos abuse toolkit | net462 |
| Seatbelt | Security enumeration | net462 |
| Certify | ADCS enumeration & abuse | net462 |
| SharpUp | Privilege escalation checks | net462 |
| SharpDPAPI | DPAPI secrets extraction | net462 |
| ForgeCert | Certificate forgery | net462 |
| SharpWMI | WMI lateral movement | net462 |
| KrbRelay | Kerberos relay attacks | net462 |
| KrbRelayUp | Kerberos relay priv-esc | net462 |
| ADSearch | AD LDAP enumeration | net462 |
| StandIn | AD post-compromise toolkit | net462 |
| Whisker | Shadow Credentials attack | net462 |
| SharpSploit | Post-exploitation library | netstandard2.0 |
| SharpKatz | C# Mimikatz (sekurlsa) | net462 |
| SharpView | C# PowerView port | net462 |
| SharPersist | Persistence toolkit | net462 |
| SharpSecDump | Remote SAM + LSA dump | net462 |
| SQLRecon | SQL Server post-exploitation | net6.0 |
| Snaffler | Credential hunting | net462 |
| InternalMonologue | NetNTLM extraction | net462 |
| SpoolSample | Print spooler coercion | net462 |

---

## Manual Building — dotnet CLI

### Basic Build (Single Tool)

```bash
# 1. Clone the repository
git clone https://github.com/GhostPack/Rubeus.git
cd Rubeus

# 2. Restore NuGet packages
dotnet restore Rubeus.sln

# 3. Build in Release mode
dotnet build Rubeus.sln -c Release

# 4. Find your binary
ls -la Rubeus/bin/Release/net462/Rubeus.exe
```

### Self-Contained Build (No .NET Required on Target)

```bash
dotnet publish Rubeus.sln -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true
# Output: Rubeus/bin/Release/net462/win-x64/publish/Rubeus.exe
```

### Targeting Specific .NET Versions

Many GhostPack tools target .NET 4.6.2 (`net462`). To build for a different version:

```bash
# Build for .NET 4.5 (older Windows Server compatibility)
dotnet build Rubeus.sln -c Release -f net45

# Build for .NET 6.0 (modern, cross-platform)
dotnet build Rubeus.sln -c Release -f net6.0
```

---

## Manual Building — Visual Studio

### Step-by-Step

1. **Install Visual Studio** (Community Edition is free)
   - During setup, select the **".NET desktop development"** workload
   - Also select **.NET Framework 4.6.2 targeting pack** under "Individual components"

2. **Clone the repository**
   ```
   File → Clone Repository → paste the GitHub URL
   ```

3. **Open the solution**
   ```
   File → Open → Project/Solution → select the .sln file
   ```

4. **Set build configuration**
   - Toolbar: Change `Debug` → `Release`
   - Toolbar: Change `Any CPU` or `x64` as needed

5. **Restore NuGet packages**
   ```
   Tools → NuGet Package Manager → Package Manager Console
   > Update-Package -reinstall
   ```

6. **Build**
   ```
   Build → Build Solution (Ctrl+Shift+B)
   ```

7. **Find your binary**
   ```
   Project\bin\Release\net462\ToolName.exe
   ```

### Visual Studio Code (Alternative)

```bash
# Install C# extension
code --install-extension ms-dotnettools.csharp

# Open the project folder
code ./Rubeus

# Use the integrated terminal to build
dotnet build Rubeus.sln -c Release
```

---

## Cross-Compilation (Linux/macOS → Windows)

You can build Windows executables from a Linux or macOS machine:

```bash
# Install .NET SDK (see Prerequisites above)

# Clone and build for Windows
git clone https://github.com/GhostPack/Rubeus.git
cd Rubeus

# Cross-compile for Windows x64
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true

# The Windows .exe will be in:
# bin/Release/net462/win-x64/publish/Rubeus.exe
```

### Important Notes

- **Mono** may be needed for .NET Framework targets on Linux: `sudo apt install mono-complete`
- Some tools require **Windows-specific APIs** and may not cross-compile cleanly
- For best results, build on a **Windows VM** or use **GitHub Actions** (see below)

### GitHub Actions (CI/CD Build Pipeline)

Create `.github/workflows/build.yml` in your fork:

```yaml
name: Build C# Tools
on: [push, workflow_dispatch]
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'
      - run: dotnet restore
      - run: dotnet build -c Release
      - uses: actions/upload-artifact@v4
        with:
          name: compiled-tools
          path: '**/bin/Release/**/*.exe'
```

---

## OPSEC Considerations

### Why Build from Source?

1. **Signature Evasion** — Pre-compiled binaries from SharpCollection and GhostPack-CompiledBinaries are heavily signatured by AV/EDR vendors
2. **Integrity** — Building from source guarantees no backdoors
3. **Customisation** — You can modify tool behaviour before compilation
4. **Obfuscation** — Integrate obfuscation into your build pipeline

### Quick Obfuscation Tips

```bash
# 1. Rename the assembly and namespace
# Edit AssemblyInfo.cs or .csproj:
# <AssemblyName>TotallyLegitProcess</AssemblyName>

# 2. Use ConfuserEx for basic obfuscation
# https://github.com/mkaring/ConfuserEx

# 3. Use InvisibilityCloak for string obfuscation
# https://github.com/h4wkst3r/InvisibilityCloak
pip install InvisibilityCloak
InvisibilityCloak -d ./Rubeus -m reverse

# 4. Build after obfuscation
dotnet build -c Release
```

### Detection Warning

These tools **will** be flagged by modern EDR solutions (CrowdStrike, Defender for Endpoint, SentinelOne) even when built from source. For real engagements:
- Use in-memory execution (Donut, Assembly.Load)
- Use D/Invoke instead of P/Invoke
- Consider BOF (Beacon Object Files) alternatives
- Time your execution carefully

---

## Troubleshooting

### Common Errors

**"The framework 'net462' was not found"**
```bash
# Install the .NET Framework targeting pack
# On Linux: install Mono
sudo apt install mono-complete mono-devel
# Or reference pack via NuGet
dotnet add package Microsoft.NETFramework.ReferenceAssemblies.net462
```

**"NuGet package not found"**
```bash
dotnet nuget add source https://api.nuget.org/v3/index.json
dotnet restore --force
```

**"Could not find file 'packages.config'"**
```bash
# This is a legacy NuGet format. Migrate:
dotnet migrate
# Or install packages manually via NuGet
```

**Build fails with MSBuild errors**
```bash
# Try using MSBuild directly (Windows)
msbuild ToolName.sln /p:Configuration=Release

# Or on Linux/macOS with Mono
msbuild ToolName.sln /p:Configuration=Release /p:TargetFrameworkVersion=v4.6.2
```

**"Assembly reference not found"**
```bash
# Ensure you have the correct SDK version
dotnet --list-sdks
# Install additional targeting packs
dotnet add package Microsoft.NETFramework.ReferenceAssemblies
```

---

## Tool Reference

### GhostPack (SpecterOps)

| Tool | Repo | Purpose |
|------|------|---------|
| Rubeus | `GhostPack/Rubeus` | Kerberoasting, AS-REP roasting, ticket manipulation, delegation abuse |
| Seatbelt | `GhostPack/Seatbelt` | Host security configuration enumeration |
| Certify | `GhostPack/Certify` | ADCS template enumeration, ESC1-ESC8 |
| SharpUp | `GhostPack/SharpUp` | Local privilege escalation checks (PowerUp equivalent) |
| SharpDPAPI | `GhostPack/SharpDPAPI` | DPAPI secret extraction (credentials, certificates) |
| ForgeCert | `GhostPack/ForgeCert` | Certificate forgery using stolen CA keys |
| SharpWMI | `GhostPack/SharpWMI` | WMI queries and lateral movement |

### AD Exploitation

| Tool | Repo | Purpose |
|------|------|---------|
| ADSearch | `tomcarver16/ADSearch` | LDAP-based AD enumeration |
| StandIn | `FuzzySecurity/StandIn` | RBCD, GPO, ACL abuse |
| Whisker | `eladshamir/Whisker` | Shadow Credentials (msDS-KeyCredentialLink) |
| SharpView | `tevora-threat/SharpView` | C# port of PowerView |
| KrbRelay | `cube0x0/KrbRelay` | Kerberos authentication relay |
| KrbRelayUp | `Dec0ne/KrbRelayUp` | Local privilege escalation via Kerberos relay |
| InternalMonologue | `eladshamir/Internal-Monologue` | NetNTLM hash extraction without touching LSASS |
| SpoolSample | `leechristensen/SpoolSample` | Print spooler coercion for unconstrained delegation |

### Post-Exploitation

| Tool | Repo | Purpose |
|------|------|---------|
| SharpKatz | `b4rtik/SharpKatz` | C# Mimikatz (sekurlsa module) |
| SharpSecDump | `G0ldenGunSec/SharpSecDump` | Remote SAM and LSA secrets dumping |
| SharPersist | `mandiant/SharPersist` | Persistence mechanism toolkit |
| SharpSploit | `cobbr/SharpSploit` | Post-exploitation library (dependency for other tools) |
| Snaffler | `SnaffCon/Snaffler` | Credential and secret hunting across file shares |
| SQLRecon | `skahwah/SQLRecon` | SQL Server reconnaissance and post-exploitation |
