#!/usr/bin/env bash
# entrypoint — runs once per container start, then hands off to CMD (zsh).
# Prepares the tun device, persisted data dirs, and gpg, then nudges first-run
# `pe init` (which must stay interactive: it sets the DB passphrase).
set -eu

# 1) TUN device for the in-container HTB VPN (harmless if already provided).
if [ ! -c /dev/net/tun ]; then
    mkdir -p /dev/net
    mknod /dev/net/tun c 10 200 2>/dev/null || true
    chmod 600 /dev/net/tun 2>/dev/null || true
fi

# 2) State/data dirs on the persisted volumes (created before first use).
mkdir -p /root/htb /root/vpn \
         /root/.local/state/zsh \
         /root/.local/state/htb \
         /root/.local/state/pentest-env \
         /root/.local/share/pentest-env
chmod 700 /root/.gnupg 2>/dev/null || true

# (First-run guidance is printed by htb.zshrc, so it shows for `exec` sessions
#  too — the entrypoint's CMD is bypassed by `docker compose exec`.)

exec "$@"
