#!/usr/bin/env bash
# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
# ──────────────────────────────────────────────────────────────────────
# VibecodersCrew source installer
# One-command source setup for macOS and Linux. Uses public python/pip
# (backend) plus npm/vite (frontend); it does not install desktop artifacts or
# provision cloud infrastructure.
#
# Usage (from a local clone):
#   git clone https://github.com/serejaris/vibecoderscrew.git
#   cd vibecoderscrew
#   bash install.sh
#
# Options:
#   --voice   Install optional voice extras (pip install -e .[voice])
#   --mise    Use mise (https://mise.jdx.dev) for Python and Node.js
#             instead of system package managers. Does not modify your
#             global mise config.
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

# Isolate the managed venv from any inherited PYTHONPATH/PYTHONHOME. If the
# caller's environment points these at foreign site-packages (e.g. another
# app's interpreter on a different Python version), pip treats those packages
# as already satisfied and silently skips installing our dependencies into the
# venv -- producing a broken install (ImportError: No module named 'aiohttp').
unset PYTHONPATH PYTHONHOME

# ── Parse arguments ──
USE_MISE=0
WITH_VOICE=0
for _arg in "$@"; do
    case "$_arg" in
        --mise)  USE_MISE=1 ;;
        --voice) WITH_VOICE=1 ;;
        *) echo "Error: unknown argument '$_arg'" >&2; exit 1 ;;
    esac
done

# ── Constants ──
# Repo root = directory containing this script (run from a local clone).
VIBECODERSCREW_APP_DIR="$(cd "$(dirname "$0")" && pwd)"
# Technical path variable retained for the Python package's compatibility
# environment names; all user-facing commands use VibecodersCrew below.
KIROCREW_APP_DIR="$VIBECODERSCREW_APP_DIR"
# Data home: honor KIROCREW_HOME, else the current default ~/.kiro/crew (NOT the
# pre-move ~/.kirocrew, which the one-time data-home migration deletes).
KIROCREW_DATA_DIR="${KIROCREW_HOME:-$HOME/.kiro/crew}"
NODE_VERSION="20"
PYTHON_VERSION="3.12"
KIROCREW_PORT="${KIROCREW_PORT:-5476}"

# ── Colors & Formatting ──
if [ -t 1 ] && command -v tput >/dev/null 2>&1; then
    BOLD=$(tput bold)
    DIM=$(tput dim)
    RESET=$(tput sgr0)
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4)
    MAGENTA=$(tput setaf 5)
    CYAN=$(tput setaf 6)
else
    BOLD="" DIM="" RESET=""
    RED="" GREEN="" YELLOW="" BLUE="" MAGENTA="" CYAN=""
fi

# ── UI Helpers ──
_STEP=0
_TOTAL_STEPS=4

banner() {
    echo ""
    echo "${MAGENTA}${BOLD}"
    cat << 'BANNER'
   _  ___           ___ _
  | |/ (_)_ _ ___  / __| |__ ___ __ __
  | ' <| | '_/ _ \| (__| / _` \ V  V /
  |_|\_\_|_| \___/ \___|_\__,_|\_/\_/
BANNER
    echo "${RESET}"
    echo "  ${DIM}Your personal AI agent${RESET}"
    echo "  ${DIM}────────────────────────────────────────${RESET}"
    echo ""
}

step() {
    _STEP=$((_STEP + 1))
    echo ""
    echo "  ${BLUE}${BOLD}[$_STEP/$_TOTAL_STEPS]${RESET} ${BOLD}$1${RESET}"
    echo "  ${DIM}$(printf '%.0s─' $(seq 1 50))${RESET}"
}

info()    { echo "  ${DIM}→${RESET} $1"; }
ok()      { echo "  ${GREEN}✓${RESET} $1"; }
warn()    { echo "  ${YELLOW}⚠${RESET} $1"; }
fail()    { echo "  ${RED}✗${RESET} $1"; }
detail()  { echo "    ${DIM}$1${RESET}"; }

die() {
    echo ""
    fail "$1"
    echo ""
    echo "  ${DIM}Need help? See the README or open an issue on GitHub.${RESET}"
    echo ""
    exit 1
}

spinner() {
    local pid=$1 msg=$2
    local frames='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        printf "\r  ${DIM}%s${RESET} %s" "${frames:i%${#frames}:1}" "$msg"
        i=$((i + 1))
        sleep 0.1
    done
    printf "\r"
}

has() { command -v "$1" >/dev/null 2>&1; }

# ── Pre-flight ──

banner

echo "  ${DIM}Repo directory:${RESET}     $KIROCREW_APP_DIR"
echo "  ${DIM}Data directory:${RESET}     $KIROCREW_DATA_DIR"
echo "  ${DIM}Platform:${RESET}           $(uname -s) $(uname -m)"
echo ""

if [ ! -f "$VIBECODERSCREW_APP_DIR/pyproject.toml" ]; then
    die "Run this from inside a VibecodersCrew clone (pyproject.toml not found in $VIBECODERSCREW_APP_DIR).
     git clone https://github.com/serejaris/vibecoderscrew.git && cd vibecoderscrew && bash install.sh"
fi

# ══════════════════════════════════════════════════════════════════════
# Step 1: Dependencies
# ══════════════════════════════════════════════════════════════════════
step "Dependencies"

# ── mise runtimes (opt-in via --mise) ──
if [ "$USE_MISE" -eq 1 ]; then
    if ! has mise; then
        info "Installing mise…"
        curl -fsSL https://mise.run | sh || true
        export PATH="$HOME/.local/bin:$PATH"
        has mise || die "mise installation failed. Install manually: https://mise.jdx.dev/installing-mise.html"
    fi
    ok "mise $("$HOME/.local/bin/mise" version 2>/dev/null || mise version)"

    _mise_log=$(mktemp)

    info "Installing Python $PYTHON_VERSION via mise…"
    mise install "python@$PYTHON_VERSION" -y 2>"$_mise_log" \
        || { cat "$_mise_log" >&2; die "Failed to install Python $PYTHON_VERSION via mise"; }
    _py_prefix="$(mise where "python@$PYTHON_VERSION")" \
        || die "mise installed Python but 'mise where' failed — check mise status"
    [ -n "$_py_prefix" ] || die "mise where returned an empty path for Python"
    [ -x "$_py_prefix/bin/python3" ] \
        || die "Python binary not found at $_py_prefix/bin/python3"
    _py="$_py_prefix/bin/python3"
    _py_ver=$("$_py" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')")
    ok "Python $_py_ver ($_py) [mise]"

    info "Installing Node.js $NODE_VERSION via mise…"
    mise install "node@$NODE_VERSION" -y 2>"$_mise_log" \
        || { cat "$_mise_log" >&2; die "Failed to install Node.js $NODE_VERSION via mise"; }
    _node_prefix="$(mise where "node@$NODE_VERSION")" \
        || die "mise installed Node.js but 'mise where' failed — check mise status"
    [ -n "$_node_prefix" ] || die "mise where returned an empty path for Node.js"
    [ -x "$_node_prefix/bin/node" ] \
        || die "Node binary not found at $_node_prefix/bin/node"
    export PATH="$_node_prefix/bin:$_py_prefix/bin:$PATH"
    ok "Node.js $(node --version) [mise]"

    rm -f "$_mise_log"
fi

# ── Python ──
if [ "$USE_MISE" -eq 0 ]; then
info "Checking Python…"
_py=""
_find_python() {
    for _candidate in python3.12 python3.11 python3.10 python3 python; do
        if has "$_candidate"; then
            _ok=$("$_candidate" -c "import sys; print(int(sys.version_info >= (3, 10)))" 2>/dev/null || echo "0")
            if [ "$_ok" = "1" ]; then
                _ver=$("$_candidate" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')" 2>/dev/null)
                _py="$_candidate"
                ok "Python $_ver ($( which "$_candidate" ))"
                return 0
            fi
        fi
    done
    return 1
}

if ! _find_python; then
    # Try to install automatically
    if [ "$(uname)" = "Darwin" ]; then
        info "Installing Python via Xcode Command Line Tools…"
        xcode-select --install 2>/dev/null || true
        sleep 2
        if ! _find_python; then
            warn "Xcode CLT install may be in progress (check the popup)"
            detail "After it finishes, re-run this installer"
            die "Python 3.10+ required. Waiting for Xcode CLT to finish installing."
        fi
    elif has apt-get; then
        info "Installing Python 3 via apt…"
        sudo apt-get update -qq >/dev/null 2>&1
        sudo apt-get install -y python3 python3-pip python3-venv >/dev/null 2>&1
        _find_python || die "Python install failed. Run: sudo apt-get install -y python3 python3-venv"
    elif has dnf; then
        info "Installing Python 3 via dnf…"
        sudo dnf install -y python3 python3-pip >/dev/null 2>&1
        _find_python || die "Python install failed. Run: sudo dnf install -y python3"
    elif has yum; then
        info "Installing Python 3 via yum…"
        sudo yum install -y python3 python3-pip >/dev/null 2>&1
        _find_python || die "Python install failed. Run: sudo yum install -y python3"
    elif has brew; then
        info "Installing Python 3 via Homebrew…"
        brew install python@3.12 >/dev/null 2>&1 || true
        _find_python || die "Python install failed. Run: brew install python@3.12"
    else
        die "Python 3.10+ required but not found and no package manager detected.
     Install Python 3.10+ manually (https://www.python.org/downloads/) and re-run."
    fi
fi
fi # USE_MISE -eq 0 (Python)

# ── Git ──
if has git; then
    ok "git ($( git --version | head -1 ))"
else
    die "git not found. Install it first."
fi

# ── Node.js ──
if [ "$USE_MISE" -eq 0 ]; then
info "Checking Node.js…"
if has node; then
    _node_ver=$(node --version 2>/dev/null || echo "v0")
    ok "Node.js $_node_ver ($( which node ))"
elif has apt-get; then
    info "Installing nodejs via apt…"
    sudo apt-get install -y nodejs npm >/dev/null 2>&1
    has node && ok "Node.js $(node --version) installed via apt" || warn "Node.js install failed — run: sudo apt-get install -y nodejs npm"
elif has dnf; then
    info "Installing nodejs via dnf…"
    sudo dnf install -y nodejs >/dev/null 2>&1
    has node && ok "Node.js $(node --version) installed via dnf" || warn "Node.js install failed — run: sudo dnf install -y nodejs"
elif has brew; then
    info "Installing Node.js via Homebrew…"
    brew install node >/dev/null 2>&1
    has node && ok "Node.js $(node --version) installed via brew" || warn "Node.js install failed — run: brew install node"
else
    info "Installing Node.js via nvm…"
    if [ ! -d "$HOME/.nvm" ]; then
        curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash 2>/dev/null
    fi
    export NVM_DIR="$HOME/.nvm"
    # shellcheck disable=SC1091
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    nvm install "$NODE_VERSION" >/dev/null 2>&1
    nvm alias default "$NODE_VERSION" >/dev/null 2>&1
    if has node; then
        ok "Node.js $(node --version) installed via nvm"
    else
        warn "Node.js install failed — frontend build will be skipped"
        detail "Install manually: nvm install $NODE_VERSION"
    fi
fi
fi # USE_MISE -eq 0 (Node.js)

# ══════════════════════════════════════════════════════════════════════
# Step 2: Build
# ══════════════════════════════════════════════════════════════════════
step "Build"

cd "$KIROCREW_APP_DIR"

# ── Frontend (npm + vite) ──
# Vite emits to website/dist; we stage it into src/kiro_crew/static/dist
# where setup.py copies it into the package at install time.
if has node && [ -d "$KIROCREW_APP_DIR/website" ]; then
    info "Building frontend (website/)…"
    _fe_log="$(mktemp)"
    (
        cd "$KIROCREW_APP_DIR/website" &&
        if [ -f package-lock.json ]; then
            npm ci --no-audit --no-fund --loglevel=error 2>"$_fe_log"
        else
            npm install --no-audit --no-fund --loglevel=error 2>"$_fe_log"
        fi &&
        npm run build 2>>"$_fe_log"
    ) &
    spinner $! "Installing npm packages & building React app…"
    if wait $!; then
        _dist_src="$KIROCREW_APP_DIR/website/dist"
        _dist_dst="$KIROCREW_APP_DIR/src/kiro_crew/static/dist"
        if [ -d "$_dist_src" ]; then
            rm -rf "$_dist_dst"
            mkdir -p "$(dirname "$_dist_dst")"
            cp -R "$_dist_src" "$_dist_dst"
            ok "Frontend built and staged → src/kiro_crew/static/dist"
        else
            warn "website/dist not found after build — dashboard assets are unavailable"
        fi
    else
        warn "Frontend build failed — dashboard assets are unavailable"
        [ -s "$_fe_log" ] && tail -5 "$_fe_log" | while IFS= read -r _line; do detail "$_line"; done
    fi
    rm -f "$_fe_log"
else
    warn "Skipping frontend build (Node.js or website/ not available)"
    detail "Install Node.js 18+ for the full React dashboard experience"
fi

# ── Python virtual environment & package ──
info "Creating virtual environment…"
_venv="$KIROCREW_APP_DIR/.venv"
if [ -d "$_venv" ] && [ -x "$_venv/bin/python" ]; then
    ok "Existing venv found"
else
    "$_py" -m venv "$_venv" || die "Failed to create venv. You may need: $_py -m pip install virtualenv"
    ok "venv created at $_venv"
fi

info "Installing Python package…"

_pip_target="."
if [ "$WITH_VOICE" -eq 1 ]; then
    _pip_target=".[voice]"
    detail "Including voice extras (.[voice])"
fi

_pip_log="$(mktemp)"
(
    "$_venv/bin/pip" install --upgrade pip setuptools wheel 2>&1 | tail -5 > "$_pip_log"
    cd "$KIROCREW_APP_DIR"
    # Frontend already built and staged above; skip rebuild in setup.py.
    KIROCREW_SKIP_FRONTEND=1 "$_venv/bin/pip" install -e "$_pip_target" 2>&1 | tail -20 >> "$_pip_log"
) &
    spinner $! "Installing VibecodersCrew and dependencies…"
if wait $!; then
    if "$_venv/bin/python" -c "import aiohttp" 2>/dev/null; then
        ok "Python package installed (isolated venv)"
    else
        die "Package installed but dependencies missing (aiohttp not importable).
     Try manually: $_venv/bin/pip install -e $KIROCREW_APP_DIR"
    fi
else
    if [ -s "$_pip_log" ]; then
        echo ""
        tail -10 "$_pip_log" | while IFS= read -r _line; do detail "$_line"; done
        echo ""
    fi
    die "pip install failed. Check: $_venv/bin/pip --version"
fi
rm -f "$_pip_log"

# Record install method so `vibecoderscrew update` uses the right rebuild strategy
echo "pip" > "$KIROCREW_APP_DIR/.install-method"
ok "Install method recorded (.install-method=pip)"

# Symlink the canonical entry point and its technical compatibility alias to
# ~/.local/bin for PATH access.
mkdir -p "$HOME/.local/bin"
if [ -x "$_venv/bin/vibecoderscrew" ]; then
    _cli_entry="$_venv/bin/vibecoderscrew"
else
    _cli_entry="$_venv/bin/kirocrew"
fi
ln -sf "$_cli_entry" "$HOME/.local/bin/vibecoderscrew"
ln -sf "$_cli_entry" "$HOME/.local/bin/kirocrew"
ok "Symlinked vibecoderscrew (primary) and kirocrew (compatibility alias)"

# ══════════════════════════════════════════════════════════════════════
# Step 3: PATH & Shell Config
# ══════════════════════════════════════════════════════════════════════
step "PATH Configuration"

# The canonical entry point is symlinked to ~/.local/bin/vibecoderscrew.
export PATH="$HOME/.local/bin:$KIROCREW_APP_DIR/bin:$PATH"

# Persist to shell rc files
_path_line="export PATH=\"\$HOME/.local/bin:\$PATH\""
_marker="# VibecodersCrew"

_add_to_rc() {
    local rc="$1"
    [ ! -f "$rc" ] && return
    if grep -qF "$_marker" "$rc" 2>/dev/null; then
        local _tmp
        _tmp="$(mktemp)"
        awk "/$_marker/{skip=2} skip>0{skip--; next} 1" "$rc" > "$_tmp" && mv "$_tmp" "$rc"
    fi
    echo "" >> "$rc"
    echo "$_marker" >> "$rc"
    echo "$_path_line" >> "$rc"
    ok "Added to $(basename "$rc")"
}

# Also persist KIROCREW_PROJECT_DIR so vibecoderscrew works from any directory
_proj_line="export KIROCREW_PROJECT_DIR=\"$KIROCREW_APP_DIR\""

_add_proj_to_rc() {
    local rc="$1"
    [ ! -f "$rc" ] && return
    if grep -qF "KIROCREW_PROJECT_DIR" "$rc" 2>/dev/null; then
        local _tmp
        _tmp="$(mktemp)"
        grep -v "KIROCREW_PROJECT_DIR" "$rc" > "$_tmp" && mv "$_tmp" "$rc"
    fi
    echo "$_proj_line" >> "$rc"
}

export KIROCREW_PROJECT_DIR="$KIROCREW_APP_DIR"

for _rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$_rc" ]; then
        _add_to_rc "$_rc"
        _add_proj_to_rc "$_rc"
    fi
done

# ── Fish shell ──
_fish_config="$HOME/.config/fish/config.fish"
if [ -f "$_fish_config" ] || [ "$(basename "${SHELL:-}")" = "fish" ]; then
    mkdir -p "$HOME/.config/fish"
    if grep -qF "$_marker" "$_fish_config" 2>/dev/null; then
        _tmp="$(mktemp)"
        awk -v marker="$_marker" 'BEGIN{s=0} $0==marker{s=1;next} s&&/^(fish_add_path|set -gx KIROCREW)/{next} {s=0;print}' "$_fish_config" > "$_tmp" && mv "$_tmp" "$_fish_config"
    fi
    {
        echo "$_marker"
        echo "fish_add_path -g ~/.local/bin"
        echo "set -gx KIROCREW_PROJECT_DIR $KIROCREW_APP_DIR"
    } >> "$_fish_config"
    ok "Added to config.fish"
fi

# Save project dir for vibecoderscrew to find
mkdir -p "$KIROCREW_DATA_DIR"
echo "$KIROCREW_APP_DIR" > "$KIROCREW_DATA_DIR/project_dir"

# Verify the canonical command is accessible
if has vibecoderscrew; then
    ok "vibecoderscrew command available"
elif [ -x "$HOME/.local/bin/vibecoderscrew" ]; then
    ok "vibecoderscrew symlinked to ~/.local/bin/vibecoderscrew"
    detail "You may need to restart your shell for it to be in PATH"
else
    warn "vibecoderscrew not in PATH — restart your shell or run:"
    detail "source ~/.$(basename "$SHELL")rc"
fi

# ══════════════════════════════════════════════════════════════════════
# Step 4: Agent Config
# ══════════════════════════════════════════════════════════════════════
step "Agent Config"

# Install agent config via the canonical command (the alias remains a fallback
# for shells that have not refreshed PATH yet).
if has vibecoderscrew; then
    _kirocrew=vibecoderscrew
elif [ -x "$HOME/.local/bin/vibecoderscrew" ]; then
    _kirocrew="$HOME/.local/bin/vibecoderscrew"
elif has kirocrew; then
    _kirocrew=kirocrew
elif [ -x "$HOME/.local/bin/kirocrew" ]; then
    _kirocrew="$HOME/.local/bin/kirocrew"
else
    _kirocrew=""
fi
if [ -n "$_kirocrew" ]; then
    info "Installing agent config…"
    KIROCREW_PROJECT_DIR="$KIROCREW_APP_DIR" "$_kirocrew" setup --agent-only \
        && ok "Agent config installed" \
        || warn "vibecoderscrew setup --agent-only failed (run it manually after install)"
fi

ok "Run ${CYAN}vibecoderscrew setup${RESET} to configure agent, workspace, and integrations"

# ── Embeddings (optional) ──
info "Optional: semantic memory embeddings"
detail "No model downloads happen by default. Set KIROCREW_EMBED_MODEL_URL (HTTPS)"
detail "or memory.embed_model_path to a local GGUF; otherwise keyword search is used."


# ══════════════════════════════════════════════════════════════════════
# Done!
# ══════════════════════════════════════════════════════════════════════

echo ""
echo ""
echo "  ${GREEN}${BOLD}VibecodersCrew installed successfully!${RESET}"
echo ""
echo "  ${DIM}────────────────────────────────────────${RESET}"
echo ""
echo "  ${BOLD}Next steps:${RESET}"
echo ""
echo "    ${CYAN}1.${RESET} Reload your shell:"
case "$(basename "${SHELL:-}")" in
    fish) echo "       ${GREEN}source ~/.config/fish/config.fish${RESET}" ;;
    bash|zsh) echo "       ${GREEN}source ~/.$(basename "${SHELL}")rc${RESET}" ;;
    *) echo "       ${GREEN}Restart your terminal${RESET}" ;;
esac
echo ""
echo "    ${CYAN}2.${RESET} Run the setup wizard:"
echo "       ${GREEN}vibecoderscrew setup${RESET}"
echo ""
echo "    ${CYAN}3.${RESET} Start the dashboard:"
echo "       ${GREEN}vibecoderscrew gateway${RESET}"
echo ""
echo "    Provider options:"
echo "       ${GREEN}codex login && vibecoderscrew config set agent.provider codex${RESET}"
echo "       ${GREEN}install kiro-cli, then set agent.provider to acp${RESET}"
echo ""
echo "    ${CYAN}4.${RESET} Open ${CYAN}http://localhost:${KIROCREW_PORT}${RESET} in your browser"
echo ""
# SSH tunnel tip for remote Linux users
if [ "$(uname)" != "Darwin" ]; then
    _hostname=$(hostname -f 2>/dev/null || hostname)
    echo "  ${DIM}────────────────────────────────────────${RESET}"
    echo ""
    echo "  ${BOLD}Remote access:${RESET}"
    echo "    Run this on your ${CYAN}local machine${RESET} to forward the dashboard:"
    echo ""
    echo "    ${GREEN}ssh -N -L ${KIROCREW_PORT}:localhost:${KIROCREW_PORT} $_hostname${RESET}"
    echo ""
    echo "    Then open ${CYAN}http://localhost:${KIROCREW_PORT}${RESET} in your local browser."
    echo ""
fi
echo "  ${DIM}────────────────────────────────────────${RESET}"
echo ""
echo "  ${DIM}Update anytime:${RESET}  ${GREEN}git pull && bash install.sh${RESET}"
echo ""
