#!/usr/bin/env bash
# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and MODIFICATIONS.md.
#
# Desktop artifacts in this fork are source-only. The historical upstream
# signing entrypoint is retained as a named guard so callers fail closed rather
# than accidentally sending a local build to an external signing service.

set -euo pipefail

echo "VibecodersCrew is source-only; desktop signing is disabled in this fork." >&2
echo "Build and distribute from source, or sign a downstream build with your own identity." >&2
exit 77
