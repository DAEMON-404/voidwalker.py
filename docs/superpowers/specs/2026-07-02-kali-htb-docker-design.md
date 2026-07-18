# Kali HTB Docker Environment — Design

**Date:** 2026-07-02
**Status:** Approved-by-default (author away during brainstorming; recommended options taken)
**Author/driver:** Claude (Fable 5) with DAEMON

## Goal

A portable, repeatable Kali Linux Docker environment that replaces a Parallels
VM for HackTheBox Academy / Labs / CTF work on macOS or Linux, reusing the
existing **voidwalker** project as both the tool installer and the shell/tmux
environment template. The image must build and run anywhere Docker runs.

## Decisions (locked)

| Fork | Choice | Why |
| --- | --- | --- |
| Arsenal scope | **Lean HTB kit** | Curated apt list + pipx/uv/go/gem + arch-aware droppable binaries + pentest-env. Covers HTB Academy + most Pro Labs on the host's native amd64/arm64 architecture; ~4–6 GB. Skips the fragile .NET/C# `net462` source-build pipeline and heavyweight C2 servers. |
| Tool delivery | **Baked into image** | One portable artifact: run offline, `docker push`/`pull`, or `docker save` tarball. Work data lives on volumes, tools live in image layers. |
| GUI | **CLI/TUI only** | Headless container. Burp Suite / Wireshark run natively on macOS; container HTTP routes through Burp via `host.docker.internal`. XQuartz X11 documented as an optional appendix. |
| voidwalker in image | **Bundled** | `voidwalker`, `pe`, `poc`, `nse`, `exploitdb` usable inside the container; image can self-extend. |
| Base image | `${KALI_IMAGE}` (default `kalilinux/kali-rolling`) | Official multi-arch image; Docker selects the host architecture unless `DOCKER_DEFAULT_PLATFORM` requests a cross-build. |
| Prompt | voidwalker's Rose Pine `prompt.zsh` | The user's stated real preference ("voidwalker sets up kali the way I want"); starship documented as an optional swap. |

## Architecture

Single service, built in layered stages. **voidwalker is the single source of
truth**: its data lists (`APT_TOOLS`, `PIPX_TOOLS`, `GO_TOOLS`, `GEM_TOOLS`,
`UV_TOOLS`), its arch-aware binary catalog + downloader
(`install_cross_platform_tools`, `install_special_tool`), and its `pentest-env`
(`install.sh`) are reused rather than reimplemented.

```
docker/
├── Dockerfile                 # layered build; configurable official Kali base
├── Dockerfile.dockerignore    # scoped ignore (context = repo root)
├── provision.py               # DRY driver: imports voidwalker data + reuses its downloaders
├── entrypoint.sh              # first-run: tun perms, pe init hint, GPG_TTY, exec shell
├── docker-compose.yml         # caps (NET_ADMIN) + /dev/net/tun + volumes
├── .env.example               # IMAGE_TAG, KALI_IMAGE, optional cross-build platform
├── bin/hbox                    # host-side wrapper: build/up/shell/vpn/save/...
├── config/
│   ├── htb.zshrc              # container zsh tweaks (HISTFILE, GPG_TTY, PE_WORKROOT, PATH)
│   ├── htb.tmux.conf          # container tmux safety and usability tweaks
│   └── htb                    # in-container VPN + workflow helper
├── README.md
└── .gitignore                 # ignore ./work, ./vpn, .env
```

### Build layers (cache-friendly, coarse→fine)

1. **Base + toolchains + pentest-env deps** — apt core: `ca-certificates curl
   git gnupg sudo python3 python3-pip pipx golang-go ruby ruby-dev
   build-essential zsh tmux sqlcipher fzf bat ripgrep fd-find eza jq xclip bsdextrautils
   pinentry-curses openvpn iproute2 iputils-ping dnsutils openssh-client`.
2. **voidwalker install** — `COPY` the `voidwalker/` package + `pyproject.toml`
   + `README.md` + `LICENSE`; `pip install --break-system-packages`. Gives the
   `voidwalker` CLI and importable package (with bundled pentest-env assets).
3. **Arsenal apt layer** — `provision.py --print-apt` emits `APT_TOOLS` minus a
   `CONTAINER_SKIP` set (GUI/wireless: ghidra, autopsy, wireshark GUI,
   aircrack-ng, wifite, kismet, reaver, dirbuster, veil, …); batched
   `apt-get install` with per-package fallback.
4. **Language + binaries layer** — `provision.py --all`:
   - pipx: curated HTB subset of `PIPX_TOOLS`;
   - uv: `UV_TOOLS` (impacket, netexec, certipy-ad, bloodyad, bofhound);
   - go: `GO_TOOLS` (ffuf, nuclei, httpx, katana, …) via `go install`;
   - gem: `GEM_TOOLS`;
   - arch-aware binaries via voidwalker `install_cross_platform_tools()` +
     `install_special_tool()` → `~/voidwalker/tools/...` (all transfer variants,
     incl. Windows droppables), kerbrute onto PATH;
   - `WORKSPACE_DIRS` scaffold + convenience symlinks (linpeas, pspy, chisel,
     ligolo) for the host arch into `/usr/local/bin`.
5. **pentest-env deploy** — `voidwalker env --no-wm --no-theme --no-fonts
   --no-deps` (oh-my-zsh + 4 custom plugins + tpm + rc wiring + `pe` symlink).
   Then wipe any partial `pe` DB so first-run init is clean. Append container
   snippets to `~/.zshrc` / `~/.tmux.conf`.
6. **Runtime wiring** — `COPY` entrypoint + `htb` helper; `ENTRYPOINT`
   `entrypoint.sh`; default `CMD ["zsh","-l"]`.

### Networking / HTB VPN (macOS Docker Desktop reality)

- `--network host` does **not** reach the Mac LAN on Docker Desktop (host = the
  LinuxKit VM). So the HTB VPN runs **inside** the container.
- Requires `cap_add: [NET_ADMIN]` + `devices: [/dev/net/tun]`. Entrypoint
  ensures `/dev/net/tun` exists. HTB targets are reachable via `tun0` in the
  container netns; internet egress via Docker NAT.
- `htb up <file.ovpn>` starts openvpn (background) and waits for `tun0`; `htb
  down`; `htb ip`. `.ovpn` files bind-mounted read-only from the host.

### Persistence (volumes chosen to never clobber baked tools)

| Mount | Target | Type | Holds |
| --- | --- | --- | --- |
| `./work` | `/root/htb` | bind | per-box workdirs (`newbox`/`scan` write here; `PE_WORKROOT`) |
| `./vpn` | `/root/vpn` (ro) | bind | HTB `.ovpn` files |
| `htb-pe-data` | `/root/.local/share/pentest-env` | volume | encrypted flags/creds DB + backups |
| `htb-state` | `/root/.local/state` | volume | pe keyfile/active target, zsh history, VPN/runtime state; tmux panes are intentionally not serialized |

`~/.local/share` as a whole is **not** mounted (would hide baked pipx tools);
only the `pentest-env` subdir is.

### First-run behaviour (entrypoint)

1. Ensure `/dev/net/tun` (mknod if missing).
2. `export GPG_TTY`, fix perms on mounted state dirs.
3. If no `pe` DB and interactive: print a one-line hint to run `pe init` (needs
   a passphrase → must stay interactive; not auto-run).
4. `exec "$@"` (default `zsh -l`; `hbox shell` attaches tmux).

### Portability

- Self-contained `docker/` folder; build context = repo root so the build can
  reuse the `voidwalker/` package.
- `hbox save` → `docker save | gzip` tarball; `hbox load` on any machine.
- Optional registry push documented. Because tools are baked, the image runs
  fully offline.

## Non-goals (YAGNI)

- No .NET/C# source-build pipeline (drop-in prebuilt Windows binaries instead).
- No BSPWM/polybar/XFCE rice (X11 GUI; irrelevant headless).
- No wireless tooling (no radio in a container).
- No always-on GUI apps (run Burp/Wireshark on macOS).

## Verification plan

1. Static: `python3 -m py_compile provision.py`; `bash -n` on scripts; `docker
   compose config`.
2. Build: `hbox build` (Docker Desktop must be running).
3. Smoke: inside the container — `nmap --version`, `ffuf -V`, `nxc --version`,
   `impacket-secretsdump -h`, `pe help`, `voidwalker --version`, `linpeas`
   symlink present, `tmux` loads config, zsh env loads with prompt.
4. VPN: `htb up lab.ovpn` → `tun0` appears → target reachable.
