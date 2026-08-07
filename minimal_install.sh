#!/usr/bin/env bash
# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
# VibecodersCrew — minimal source install
#
# This is the short, deterministic source-install path.  It builds the in-tree
# React dashboard, installs the Python package in an isolated editable venv, and
# publishes the `vibecoderscrew` command (with the `kirocrew` compatibility
# alias).  It never downloads a model, provisions cloud infrastructure, or
# installs a provider on the user's behalf.
#
# Run from a checkout:
#   git clone https://github.com/serejaris/vibecoderscrew.git
#   cd vibecoderscrew
#   bash minimal_install.sh [--voice]
#
# Provider setup is explicit after installation:
#   Codex App Server: codex login && vibecoderscrew config set agent.provider codex
#   Kiro ACP:        install kiro-cli, then set agent.provider to acp
set -euo pipefail

unset PYTHONPATH PYTHONHOME

WITH_VOICE=0
for arg in "$@"; do
    case "$arg" in
        --voice) WITH_VOICE=1 ;;
        *) echo "error: unknown argument '$arg'" >&2; exit 2 ;;
    esac
done

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

has() { command -v "$1" >/dev/null 2>&1; }
die() { echo "error: $1" >&2; exit 1; }

has git || die "git is required"
has npm || die "npm is required to build the dashboard (install Node.js 18+ first)"
has node || die "Node.js 18+ is required to build the dashboard"

PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if has "$candidate" && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
[ -n "$PYTHON" ] || die "Python 3.10+ is required"

echo "VibecodersCrew source install"
echo "  checkout: $REPO_DIR"
echo "  python:   $("$PYTHON" --version 2>&1)"
echo "  node:     $(node --version)"

if [ -d "$REPO_DIR/website" ]; then
    echo "→ Building website/"
    (
        cd "$REPO_DIR/website"
        if [ -f package-lock.json ]; then
            npm ci --no-audit --no-fund --loglevel=error
        else
            npm install --no-audit --no-fund --loglevel=error
        fi
        npm run build
    ) || die "frontend build failed"

    DIST_SRC="$REPO_DIR/website/dist"
    DIST_DST="$REPO_DIR/src/kiro_crew/static/dist"
    [ -d "$DIST_SRC" ] || die "frontend build did not produce website/dist"
    rm -rf "$DIST_DST"
    mkdir -p "$(dirname "$DIST_DST")"
    cp -R "$DIST_SRC" "$DIST_DST"
    echo "✓ dashboard staged in src/kiro_crew/static/dist"
fi

VENV="$REPO_DIR/.venv"
if [ ! -x "$VENV/bin/python" ]; then
    echo "→ Creating $VENV"
    "$PYTHON" -m venv "$VENV" || die "could not create virtual environment"
fi

echo "→ Installing editable Python package"
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel >/dev/null
if [ "$WITH_VOICE" -eq 1 ]; then
    PIP_TARGET="${REPO_DIR}[voice]"
else
    PIP_TARGET="$REPO_DIR"
fi
KIROCREW_SKIP_FRONTEND=1 "$VENV/bin/python" -m pip install -e "$PIP_TARGET" \
    || die "pip install failed"

CLI="$VENV/bin/vibecoderscrew"
[ -x "$CLI" ] || die "vibecoderscrew entry point was not installed"
mkdir -p "$HOME/.local/bin"
ln -sf "$CLI" "$HOME/.local/bin/vibecoderscrew"
ln -sf "$CLI" "$HOME/.local/bin/kirocrew"
echo "✓ installed ~/.local/bin/vibecoderscrew"
echo "✓ installed ~/.local/bin/kirocrew (compatibility alias)"

echo
echo "Next steps:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo "  vibecoderscrew setup --agent-only"
echo "  vibecoderscrew config set agent.provider codex  # Codex App Server"
echo "  codex login"
echo "  vibecoderscrew gateway"
echo
echo "For ACP, install kiro-cli separately and set agent.provider to acp."
