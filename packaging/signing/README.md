<!-- Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew). See NOTICE and MODIFICATIONS.md. -->
# Source-only packaging records

This directory preserves a small, auditable slice of the upstream KiroCrew
Apache-2.0 release scaffolding. VibecodersCrew is distributed as source-only:
the fork does not operate an enterprise signing service or publish signed
desktop and wheel artifacts.

## Desktop signing

The desktop entrypoints are deliberately fail-closed:

- `sign.sh` and `sign-dmg.sh` exit with status `77` and explain that signing is
  disabled for this source-only fork.
- `generate-manifest.py` keeps bundle-inspection helpers for downstream
  distributors, while its command-line entrypoint is disabled.
- `manifest-template.json` is marked `source_only` and contains no upstream
  certificate, team, cloud role, or artifact-location identifiers.
- `Entitlements.entitlements` remains useful when a downstream distributor
  chooses to sign a local Electron build with its own Apple identity.

No Amazon bundle identifier, team identifier, signing endpoint, or cloud role
is a current VibecodersCrew release assumption. A downstream distributor must
provide and verify its own identity and release process.

## CLI manifest helper

`cli-manifest.py` is retained as a compatibility and provenance helper for the
strict CLI installer contract. It verifies canonical envelopes and never reads
private keys. The committed `cli-manifest-public.pem` is intentionally
`UNCONFIGURED`, so this checkout has no enabled artifact trust root. The public
fork does not enable the upstream publication workflow; do not generate or
commit a private key here.

The upstream relationship and all fork changes are recorded in the repository
root [`NOTICE`](../../NOTICE) and [`MODIFICATIONS.md`](../../MODIFICATIONS.md).
