<!-- Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew). -->
<!-- See NOTICE and CHANGELOG.md for the nature of the modifications. -->
# Historical upstream signing runbook

This file is retained as provenance for the upstream Kiro Crew repository. It
is **not an operational runbook for VibecodersCrew**. The community fork is
source-only: it does not publish signed desktop artifacts, invoke a cloud
signing service, notarize bundles, upload release artifacts, or store signing
credentials.

## Current VibecodersCrew guidance

- Treat `packaging/signing/` as historical downstream tooling and source
  reference only. The public signing entry points fail closed.
- Do not copy upstream signing identities, account identifiers, endpoints,
  roles, credential names, or release commands into this fork.
- Build and distribute from source according to [docs/install.md](install.md)
  and [docs/desktop-app.md](desktop-app.md). Any downstream distributor that
  signs a private build must provide its own application identity, certificates,
  artifact transport, and credential custody.
- The current bundle identity is `dev.serejaris.vibecoderscrew` (nightly:
  `dev.serejaris.vibecoderscrew.nightly`). It is unrelated to the upstream
  signing account and must not be sent to an upstream signing service.

## Historical provenance

The upstream Kiro Crew project documented a macOS chain involving an Electron
bundle, a signing-manifest generator, a hosted signer, Apple notarization, and
stapling. That material is preserved in the upstream repository history for
auditing context; its identities, credentials, commands, and infrastructure
are intentionally omitted from this current fork's guidance so they cannot be
mistaken for an approved release path.

See the [upstream Kiro Crew repository](https://github.com/kirodotdev/KiroCrew)
and its historical file history for the original operational details.

## Source-only release boundary

`MODIFICATIONS.md` records the fork's distribution boundary. The manifest
template and generator remain only to make the historical code path explicit;
they do not authorize signing or publication. A downstream distributor is
responsible for an independent security review before using any retained
helper.
