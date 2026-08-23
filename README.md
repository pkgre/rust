# rust.pkg.re

Public declarative curated Cargo sparse registries served at [rust.pkg.re](https://rust.pkg.re/).

| Registry | Sparse index | Source class | Archive download |
|---|---|---|---|
| `universe` | `sparse+https://rust.pkg.re/universe/` | crates.io mirror | `https://static.crates.io/crates` |
| `pkgre` | `sparse+https://rust.pkg.re/pkgre/` | approved first-party Git tags | `https://rust.pkg.re/crates/{sha256-checksum}.crate` |

A registry is mirror-only or Git-only because Cargo exposes one `dl` URL per registry; [`pkgre-indexer`](https://github.com/pkgre/pkgre) rejects mixed source classes. `universe` controls admitted metadata + checksums while Cargo downloads checksum-constrained mirror bytes directly from crates.io; mirrored `.crate` files are not committed. `pkgre` retains + serves only active content-addressed Git publication archives.

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

`registry/{universe,pkgre}.toml` + external category files = complete human-edited desired state: fixed registry/category policy + exact crates.io mirror versions + approved first-party HTTPS Git tags. `pkgre-indexer lock` reconciles that state into canonical adjacent locks + content-addressed objects; validates permanent package homes, source classes, and category dependency edges; renders the Pages site from scratch; verifies byte identity; rejects mutation, disappearance, reactivation, or source-class mixing.

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
| `registry/<registry>.lock` | Generated authority: permanent category/source-class homes, lifecycle, archive/source-row/routed-row hashes, immutable Git provenance |
| `registry/objects/crates/<sha256>.crate` | Exact active Git publication archives; mirror archives are checksum-verified then discarded |
| `registry/objects/rows/<sha256>.json` | Exact retained unrouted source rows, including removed identities |

Curator schema/workflows/security documentation: [pkgre/pkgre](https://github.com/pkgre/pkgre).

## License

Curator-authored catalog metadata + repository documentation: Apache-2.0. Retained first-party package archives: each package's own license; inclusion does not relicense them.
