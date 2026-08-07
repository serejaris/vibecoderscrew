# Modifications (Apache-2.0 §4(b))

VibecodersCrew is an independent community fork of
[KiroCrew](https://github.com/kirodotdev/KiroCrew) (Apache-2.0).

Modified 2026 by Sereja Ris. Not affiliated with Amazon or OpenAI.

## Nature of modifications

1. **OpenAI Codex provider** — App Server integration using an existing ChatGPT/Codex login.
2. **Product identity** — rebranded to VibecodersCrew (`dev.serejaris.vibecoderscrew`; nightly: `.nightly`); repository `serejaris/vibecoderscrew`.
3. **Telemetry** — outbound product telemetry hard-disabled (beacon, install receipts, local product metrics, OTLP, Electron profiling).
4. **Embeddings** — in-process Qwen3 GGUF runtime with no default network fetch; an explicit HTTPS URL or local model path enables embeddings, and absent models fall back to keyword/FTS search.
5. **Distribution** — source-only public releases; public CI does not publish desktop or wheel artifacts.
6. **Upstream automation** — Amazon signing/CDN/update lanes are not used for community distribution.
7. **Public site** — landing-page copy, install commands, repository links, FAQ, and architecture labels identify VibecodersCrew and the current source-only behavior. Upstream install URLs and retired Bedrock/ACP/privacy claims are removed from current product copy.
8. **Desktop signing** — `packaging/signing/sign.sh`, `sign-dmg.sh`, and the manifest generator fail closed for the source-only fork; the old Amazon bundle identity, team identifier, signing endpoint, and cloud roles are not retained as release assumptions.
9. **Modification notices** — modified source and text files carry a short
   VibecodersCrew notice where their syntax permits it. JSON, locale catalogs,
   lockfiles, generated bundles, and other generated assets are covered by
   this aggregate file, `NOTICE`, and `THIRD-PARTY-NOTICES`.
10. **Dependency provenance** — `THIRD-PARTY-NOTICES` is regenerated from the
    production graphs in `website/`, `site/`, and `website/electron/`, plus
    the resolved Python runtime environment. It records exact versions,
    SPDX identifiers, source/integrity evidence, and license text. Vendored
    `llama-cpp-python` 0.3.34 is recorded separately with its 26-file native
    closure and source artifact hashes.

## Notice form

Modified source files carry a short header comment pointing here and to `NOTICE` / `CHANGELOG.md`. Binary and pure-JSON assets are covered by this file and `NOTICE`.

## Technical identifiers retained

- Python import path `kiro_crew` (mergeability with upstream).
- CLI alias `kirocrew` (compatibility); primary entry point is `vibecoderscrew`.
- Default data home `~/.kiro/crew` (existing installs); override with `KIROCREW_HOME`.

These are technical paths, not the public product name.
