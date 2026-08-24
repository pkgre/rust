# rust.pkg.re

Public declarative curated Cargo sparse registries served at [rust.pkg.re](https://rust.pkg.re/).

| Registry | Sparse index | Source class | Archive download |
|---|---|---|---|
| `universe` | `sparse+https://rust.pkg.re/universe/` | crates.io mirror | `https://dl.rust.pkg.re/v1/universe/{crate}/{version}/{sha256-checksum}` |
| `pkgre` | `sparse+https://rust.pkg.re/pkgre/` | approved first-party Git tags | `https://dl.rust.pkg.re/v1/pkgre/{crate}/{version}/{sha256-checksum}` |

Cargo exposes one `dl` URL per registry. The generated `registry/downloads.json` binds every active `(registry,name,version,sha256)` identity to its locked `crates-io` or `git-tag` source class. Both production declarations use their exact registry-bound checksum-bearing router template. The stateless router derives only hardcoded source-specific destinations: `universe` redirects checksum-constrained mirror identities to crates.io without committing them; `pkgre` redirects approved Git identities to active content-addressed publication archives. [`pkgre-indexer`](https://github.com/pkgre/pkgre) permits a mixed-source registry only when its `download` value is that registry's exact router template.

## Categories

Categories are catalog policy identities, not Cargo registry aliases. Every package has one permanent `<registry>/<category>` home; each category declares the complete set of category identities its packages may depend on.

| Category | Scope | May depend on |
|---|---|---|
| `universe/general` | General crates.io packages | `universe/general` |
| `universe/acp` | Agent Client Protocol packages | `universe/acp`, `universe/general` |
| `universe/filesystem` | Filesystem notification packages | `universe/filesystem`, `universe/general` |
| `universe/matrix` | Matrix/Ruma package family | `universe/matrix`, `universe/general` |
| `universe/mcp` | Model Context Protocol packages | `universe/mcp`, `universe/sse`, `universe/general` |
| `universe/sse` | Server-sent event packages | `universe/sse`, `universe/general` |
| `universe/terminal` | Terminal/PTY packages | `universe/terminal`, `universe/general` |
| `universe/yaml` | YAML packages | `universe/yaml`, `universe/general` |
| `pkgre/tooling` | pkg.re first-party tools | `pkgre/tooling`, `universe/general` |

Small categories are inline under `[categories.<name>]` in `registry/<registry>.toml`; large categories use `file = "categories/<registry>/<category>.toml"`. An external file contains that category's `schema`, `may-depend-on`, and `mirror` or `publish` declaration.

## Model

`registry/{universe,pkgre}.toml` + external category files = complete human-edited desired state: fixed registry/category policy + exact crates.io mirror versions + approved first-party HTTPS Git tags. New mirror identities/versions enter an established catalog only through evidence-bound batch admission with `update-plan`/`update-inspect`/`update-apply`; direct `lock` admission is rejected. `lock` handles initial bootstrap, empty name reservations, removals, and Git publication tags; reconciles permitted state into canonical adjacent locks + content-addressed objects + `downloads.json`; validates permanent package homes, source classes, category dependency edges, and router-bound mixed-source policy; renders the Pages site from scratch; verifies byte identity; rejects mutation, disappearance, reactivation, or unsafe source-class mixing.

`update-plan` writes its review template outside `registry/`; it does not create an intermediate repository state or PR. After optional evidence edits, `update-apply` atomically installs the exact manifest, generated evidence lock, declarations, registry locks, and row objects together; one batch therefore has one fully applied registry PR. CI rejects an unpaired, stale, orphaned, or catalog-unbound admission through `check`, then runs `lock` and rejects any resulting tracked or untracked `registry/` change.

Imported packages retain exact crates.io checksums + source rows. First-party releases lock Git tag object + peeled commit + package path + Cargo version, require explicit curated-registry routing, and package twice byte-identically under pinned Cargo.

Removal = retain package key but remove version/tag from the human list → lock transitions `active→removed` irreversibly; source row remains; rendered row becomes yanked; an unshared Git archive is deleted and no longer served. Re-adding a removed identity fails closed.

Approval means an exact artifact was admitted; not a warranty that package code is benign, correct, or maintained. Builds should remain isolated because approved build scripts/procedural macros execute code.

## Consumer configuration

```toml
[registries]
universe = { index = "sparse+https://rust.pkg.re/universe/" }
pkgre = { index = "sparse+https://rust.pkg.re/pkgre/" }

[registry]
default = "universe"

[source.crates-io]
replace-with = "disabled-crates-io"

[source.disabled-crates-io]
directory = "vendor/empty"
```

Every mirrored manifest dependency should set `registry = "universe"`; first-party pkg.re tools should set `registry = "pkgre"`. Commit `vendor/empty/.gitkeep`; commit the lockfile; use `cargo build --locked` or `--frozen`. Cargo has no universal registry allowlist; committed row validation + explicit routing remain part of the security boundary.

## Repository

| Path | Authority/purpose |
|---|---|
| `registry/<registry>.toml` | Human authority: registry policy + inline category declarations |
| `registry/categories/<registry>/<category>.toml` | Human authority: one large external category declaration |
| `registry/<registry>.lock` | Generated authority: permanent category/source-class homes, lifecycle, archive/source-row/routed-row hashes, immutable Git provenance, updater admission bindings |
| `registry/downloads.json` | Generated canonical router projection: one source-class route per active checksum-bound package identity |
| `registry/admissions/<batch>.toml` | Human authority: canonical exact package/version/category requests + optional typed review evidence |
| `registry/admissions/<batch>.lock` | Generated evidence: policy/API/archive/source facts for the complete batch; every admitted package binds its SHA-256 |
| `registry/objects/crates/<sha256>.crate` | Exact active Git publication archives; mirror archives are checksum-verified then discarded |
| `registry/objects/rows/<sha256>.json` | Exact retained unrouted source rows, including removed identities |

Curator schema/workflows/security documentation: [pkgre/pkgre](https://github.com/pkgre/pkgre).

## License

Curator-authored catalog metadata + repository documentation: Apache-2.0. Retained first-party package archives: each package's own license; inclusion does not relicense them.
