# syntax=docker/dockerfile:1.7
#
# Kali HTB box — a headless, repeatable pentest environment that reuses the
# VoidWalker project as both the tool installer and the zsh/tmux/pe environment.
#
# Build context is the REPO ROOT (so the voidwalker package is available):
#     docker build -f docker/Dockerfile -t htb-kali:latest .
# or just use  docker/bin/hbox build.
#
# Layers go coarse -> fine so editing a tool list doesn't rebuild the base.

ARG KALI_IMAGE=kalilinux/kali-rolling
FROM ${KALI_IMAGE} AS base

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TERM=xterm-256color \
    HOME=/root \
    GOPATH=/root/go \
    PE_WORKROOT=/root/htb \
    PATH=/root/.local/bin:/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# ── Layer 1: base deps + language toolchains + pentest-env deps ───────────────
# Kept in one cached layer because these rarely change. tshark/tcpdump replace
# the wireshark GUI; pinentry-curses lets `pe init` prompt for its DB passphrase.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl wget git gnupg2 sudo tzdata less procps psmisc file \
      python3 python3-pip python3-venv python3-dev pipx \
      golang-go ruby ruby-dev \
      build-essential pkg-config \
      zsh tmux sqlcipher fzf bat ripgrep fd-find eza jq xclip bsdextrautils \
      pinentry-curses \
      openvpn openresolv iproute2 iputils-ping net-tools dnsutils tcpdump tshark \
      openssh-client rlwrap && \
    ln -sf /usr/bin/pinentry-curses /usr/bin/pinentry

# gpg-agent uses the curses pinentry (no X in the container).
RUN mkdir -p /root/.gnupg && chmod 700 /root/.gnupg && \
    printf 'pinentry-program /usr/bin/pinentry-curses\n' > /root/.gnupg/gpg-agent.conf

# ── Layer 2: install VoidWalker (CLI + importable package + bundled assets) ───
# Only the package + packaging metadata are copied, so this layer's cache is
# invalidated by code changes, not by touching docker/ or work data.
COPY pyproject.toml README.md LICENSE MANIFEST.in /opt/voidwalker/
COPY voidwalker /opt/voidwalker/voidwalker
RUN python3 -m pip install --no-cache-dir --break-system-packages /opt/voidwalker

# The provisioning driver imports voidwalker's catalog and reuses its downloaders.
COPY docker/provision.py /opt/htb/provision.py

# ── Layer 3: curated apt arsenal (list generated from voidwalker.data) ────────
# Batched install with per-package fallback so one unavailable package on this
# arch never aborts the build.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    PKGS="$(python3 /opt/htb/provision.py --print-apt)" && \
    echo "arsenal packages: $PKGS" && \
    apt-get install -y --no-install-recommends $PKGS || \
    for p in $PKGS; do apt-get install -y --no-install-recommends "$p" || true; done && \
    ( [ -f /usr/share/wordlists/rockyou.txt.gz ] && gunzip -f /usr/share/wordlists/rockyou.txt.gz || true )

# ── Layer 4: language tools + arch-aware droppable binaries ───────────────────
# pipx (curated) / uv (impacket,netexec,certipy,bloodyad,bofhound) / go (ffuf,
# nuclei,httpx,…) / gems, then VoidWalker downloads every transfer-binary
# variant (linpeas, pspy, chisel, ligolo-ng, kerbrute, SharpHound/Rubeus/
# mimikatz droppables) into ~/voidwalker/tools and symlinks the host-arch ones.
RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=cache,target=/root/go/pkg,sharing=locked \
    python3 /opt/htb/provision.py --all

# ── Layer 5: deploy the pentest-env (zsh + tmux + pe), minus GUI rice ─────────
# --no-wm/--no-theme/--no-fonts strip X11/GUI; --no-deps because layer 1 already
# has them. `pe init` at the end is interactive (GPG passphrase) so it fails
# harmlessly here; we wipe any partial DB and defer init to first run.
# Run install.sh straight from the copied source (robust — no reliance on
# package-data packaging), capture its log, then wipe the partial DB.
RUN set -eu; \
    bash /opt/voidwalker/voidwalker/integrations/assets/pentest-env/install.sh \
        --no-wm --no-theme --no-fonts --no-deps </dev/null >/tmp/pe-install.log 2>&1 || true; \
    tail -n 25 /tmp/pe-install.log || true; \
    rm -rf /root/.local/share/pentest-env /root/.local/state/pentest-env; \
    chsh -s "$(command -v zsh)" root || true

# Container-specific shell/tmux tweaks (persistent shell history, GPG_TTY,
# PATH to ~/voidwalker tools, and zsh as tmux's login shell). Appended after
# the pentest-env blocks. Tmux pane/process state is intentionally not saved.
COPY docker/config/htb.zshrc /opt/htb/config/htb.zshrc
COPY docker/config/htb.tmux.conf /opt/htb/config/htb.tmux.conf
COPY docker/config/htb /usr/local/bin/htb
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/htb /usr/local/bin/entrypoint && \
    printf '\n# >>> htb-container >>>\n[ -f /opt/htb/config/htb.zshrc ] && source /opt/htb/config/htb.zshrc\n# <<< htb-container <<<\n' >> /root/.zshrc && \
    printf '\nsource-file -q /opt/htb/config/htb.tmux.conf\n' >> /root/.tmux.conf

WORKDIR /root/htb
ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["zsh", "-l"]
