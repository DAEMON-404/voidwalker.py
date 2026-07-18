# HTB Kali Box (Docker)

A headless, repeatable Kali Linux pentest environment for HackTheBox
Academy / Labs / CTFs — a drop-in replacement for a Parallels VM on macOS.

It **reuses [VoidWalker](../README.md)** (this repo) as the engine:

- VoidWalker's arch-aware downloader fetches the droppable arsenal
  (linpeas, pspy, chisel, ligolo-ng, kerbrute, static nc/socat, plus
  SharpHound/Rubeus/mimikatz Windows droppables).
- VoidWalker's package lists drive apt/pipx/uv/go/gem installs.
- VoidWalker's `pentest-env` gives the exact zsh + tmux + `pe` workspace you
  already use (Rose Pine prompt, cheatsheets, encrypted flags/creds DB) — just
  without the X11/GUI rice, since this is headless.

The `voidwalker`, `pe`, `poc`, `nse`, and `exploitdb` commands are all available
inside the box, so you can extend it at runtime.

---

## 1. Prerequisites

```bash
# Docker Desktop must be installed AND running.
open -a Docker          # start it if the whale icon isn't up
docker info             # should print server info (not an error)
docker compose version  # v2+
```

Docker selects the host's native architecture. For an intentional cross-build,
set `DOCKER_DEFAULT_PLATFORM` in `.env` (for example, `linux/amd64`).

## 2. First-time setup

```bash
cd docker
cp .env.example .env            # optional: tweak image/base tags
./bin/hbox build                # ~20-40 min once; downloads + bakes the arsenal
./bin/hbox up                   # start the box (detached)
./bin/hbox shell                # attach a tmux session inside it
```

Put this on your PATH to drop the `./bin/` prefix:

```bash
echo 'export PATH="$HOME/git/voidwalker.py/docker/bin:$PATH"' >> ~/.zshrc
```

## 3. Inside the box (post-setup, run once)

```bash
pe init                         # set a passphrase; creates the encrypted DB
newbox Cap 10.10.10.245         # register+activate a target, cd into ~/htb/Cap
pe cheat env                    # tour of how pe/tmux/aliases fit together
```

The prompt and tmux status bar show the active target. `prefix` is `C-a` **or**
`C-b`; `prefix + P` lays out the 3-pane HTB workspace.

## 4. HTB VPN

The VPN runs **inside** the container (Docker Desktop for Mac can't reach the
Mac LAN via host networking). Drop `.ovpn` files in `docker/vpn/`, then:

```bash
hbox vpn up lab.ovpn            # from the host  (or, inside the box:  htb up lab.ovpn)
hbox vpn status                 # tun0 address + route
hbox vpn down
```

## 5. Everyday workflow

```bash
hbox up                         # start
hbox shell                      # create/attach tmux while the box is running
hbox vpn up comp.ovpn
# ... inside: newbox Blackfield 10.10.10.192 ; scan ; nxc smb $IP ; ffuf ...
hbox stop                       # stop; DB, history, and work persist (tmux does not)
```

Burp Suite / Wireshark: run them **natively on macOS**. Route container HTTP
through Burp with `burpenv` (sets `http_proxy` to `host.docker.internal:8080`)
or `burpcurl <url>`. Capture packets in-box with `tcpdump -w cap.pcap`, open on
the Mac.

## 6. Persistence

Baked into the image (repeatable build): all tools + the shell/tmux env.
On volumes (your data survives rebuilds):

| Host / volume | In container | Contents |
| --- | --- | --- |
| `docker/work/` | `/root/htb` | per-box workdirs |
| `docker/vpn/` | `/root/vpn` (ro) | `.ovpn` files |
| `htb-pe-data` | `…/share/pentest-env` | encrypted flags/creds DB + backups |
| `htb-state` | `/root/.local/state` | pe key, zsh history, VPN/runtime state |

Back up the encrypted DB anytime with `pe backup` (inside the box); restore with
`pe restore`.

Tmux state is intentionally not serialized. Pane commands, process arguments,
and captured output can contain targets, tokens, or passwords. You can detach
and run `hbox shell` again while the container remains running; after `hbox
stop`, `hbox down`, or container recreation, `hbox shell` starts a fresh tmux
session. The work directory, shell history, and encrypted `pe` data still
survive through the mounts listed above.

## 7. Portability — run it anywhere

```bash
# A) Rebuild from source on any machine with Docker:
git clone <repo> && cd voidwalker.py/docker && ./bin/hbox build

# B) Ship the built image as a tarball (offline, no rebuild):
hbox save htb-kali.tgz          # on the source machine
#   copy htb-kali.tgz across, then:
hbox load htb-kali.tgz          # on the target machine

# C) Push to a registry:
hbox push ghcr.io/<you>/htb-kali:latest
```

## 8. Verification checklist

```bash
hbox shell        # then, inside:
nmap --version;  ffuf -V;  nxc --version;  impacket-secretsdump 2>&1 | head -1
which linpeas pspy chisel kerbrute
pe help;  voidwalker --version
tmux ls || tmux           # config loads, Rose Pine status bar shows
htb up lab.ovpn && htb status   # tun0 comes up; then reach a target
```

## Optional: starship prompt

The box ships VoidWalker's custom Rose Pine `prompt.zsh`. To swap in
[starship](https://starship.rs) instead:

```bash
# inside the box
curl -sS https://starship.rs/install.sh | sh -s -- -y
# comment the prompt.zsh source line in the pentest-env zsh block and add:
echo 'eval "$(starship init zsh)"' >> ~/.zshrc
```

## Optional: GUI apps via XQuartz

Prefer native macOS Burp/Wireshark. If you truly need in-container GUIs: install
[XQuartz](https://www.xquartz.org), `xhost +127.0.0.1`, add `-e
DISPLAY=host.docker.internal:0` to the run, and `apt install` the GUI packages.
Heavier and fiddlier than the native-macOS route.
