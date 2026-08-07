<!-- Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew). See NOTICE and CHANGELOG.md. -->
# VibecodersCrew Source Release Process

VibecodersCrew publishes source-first GitHub releases from `codex-main`. The
public fork does not publish desktop installers, binary update feeds, signing
artifacts, or a hosted package feed. GitHub's generated source archive and the
repository checkout are the supported release inputs.

The current corrective candidate is **v1.0.1**. Release metadata is prepared;
validation and external release publication remain **pending** until the
maintainer records them in the release notes.

## Current contract

- **Product:** VibecodersCrew
- **CLI:** `vibecoderscrew` (with `kirocrew` retained as a compatibility alias)
- **Desktop identity:** `dev.serejaris.vibecoderscrew`
- **Repository:** `serejaris/vibecoderscrew`
- **Distribution:** source archive or source checkout, followed by the local
  install instructions in [docs/install.md](install.md)
- **Upstream lanes:** Amazon signing, CDN, telemetry, hosted feeds, and updater
  services are outside this fork's release boundary

## Candidate checklist

| Item | v1.0.1 status |
|---|---|
| Backend and frontend product metadata | prepared |
| Source-only README and release notes | prepared |
| Source archive link | pending publication |
| Backend tests and packaging checks | pending |
| Frontend and Electron checks | pending |
| Security, license, and source-only scans | pending |

Do not replace a `pending` value with a pass claim until the corresponding
command has run against the candidate tree and its result is recorded.

## Cutting a source release

1. Update `CHANGELOG.md` and every product version root listed below.
2. Run the planned verification commands. Keep incomplete gates marked pending.
3. Review `git diff --check`, source-only boundaries, and the release notes.
4. Commit and push through the normal pull-request workflow when the maintainer
   authorizes publication.
5. Create a GitHub prerelease so GitHub supplies the source archive and notes.

Example publication command (run only after approval):

```bash
gh release create v1.0.1 --prerelease --title "VibecodersCrew v1.0.1" \
  --notes-file CHANGELOG.md
```

The release description must say that it contains source archives only and must
not promise installer downloads or update feeds.

## Version metadata

Keep all product package roots on the same bare `X.Y.Z` value:

| File | Field |
|---|---|
| `src/kiro_crew/__init__.py` | `__version__` |
| `pyproject.toml` | `[project].version` |
| `website/package.json` + lock | dashboard package version |
| `website/electron/package.json` + lock | Electron package version |
| `site/package.json` + lock | landing-site package version |

The `packages/kirocrew-client-py` package has its own compatibility version and
is intentionally not coupled to the product release.

## Historical upstream material

[`release-process-design.md`](release-process-design.md),
[`release-automation.md`](release-automation.md), and
[`signing-runbook.md`](signing-runbook.md) retain upstream provenance for
context. Their hosted-feed, signing, and binary-artifact descriptions are not
current VibecodersCrew release instructions.
