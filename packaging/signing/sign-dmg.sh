#!/usr/bin/env bash
# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and MODIFICATIONS.md.
#
# Desktop artifacts in this fork are source-only. The historical upstream DMG
# signing entrypoint is retained as a named guard so it cannot submit a local
# build to an external signing service by accident.

set -euo pipefail

echo "VibecodersCrew is source-only; DMG signing is disabled in this fork." >&2
echo "Sign a downstream build with your own Apple identity if you need a DMG." >&2
exit 77
