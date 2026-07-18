# htb.zshrc — container-only zsh tweaks, sourced after the pentest-env block.
# Keeps mutable state (history) on the persisted state volume and wires the
# bits that only make sense inside the container.
[ -n "${ZSH_VERSION:-}" ] || return 0

# History on the state volume (survives container recreation).
export HISTFILE="${XDG_STATE_HOME:-$HOME/.local/state}/zsh/history"
mkdir -p "${HISTFILE:h}" 2>/dev/null
export HISTSIZE=100000 SAVEHIST=100000
setopt inc_append_history share_history hist_ignore_all_dups

# gpg needs to know the tty to prompt for the pe DB passphrase.
export GPG_TTY="$TTY"

# Per-box work lives in ~/htb (the bind-mounted volume); newbox/scan use this.
export PE_WORKROOT="$HOME/htb"

# Tools voidwalker downloaded (host-arch ones are also symlinked into /usr/local/bin).
path=("$HOME/.local/bin" "$HOME/go/bin" /usr/local/go/bin $path)

# GUI apps run on the macOS host — route container HTTP through Burp on the Mac.
export HTB_HOST_PROXY="http://host.docker.internal:8080"
alias burpcurl='curl --proxy "$HTB_HOST_PROXY" -k'
alias burpenv='export http_proxy="$HTB_HOST_PROXY" https_proxy="$HTB_HOST_PROXY"'
alias noproxy='unset http_proxy https_proxy'

# VPN + quick status (htb helper is on PATH).
alias vpn='htb'

# First-run hint: show the quickstart until the encrypted DB is initialised.
if [[ -o interactive ]] && [[ ! -f "$HOME/.local/share/pentest-env/pentest.db" ]]; then
    print -P "%F{#c4a7e7}┌─ HTB Kali box ─────────────────────────────────────────────┐%f"
    print -P "%F{#9ccfd8}│%f pe init                 %F{#6e6a86}create your encrypted flags/creds DB%f  %F{#9ccfd8}│%f"
    print -P "%F{#9ccfd8}│%f htb up lab.ovpn         %F{#6e6a86}connect the HTB VPN (files in ./vpn)%f  %F{#9ccfd8}│%f"
    print -P "%F{#9ccfd8}│%f newbox Cap 10.10.10.245 %F{#6e6a86}register a target + make ~/htb/Cap%f     %F{#9ccfd8}│%f"
    print -P "%F{#9ccfd8}│%f pe cheat env            %F{#6e6a86}how everything fits together%f          %F{#9ccfd8}│%f"
    print -P "%F{#c4a7e7}└────────────────────────────────────────────────────────────┘%f"
fi
