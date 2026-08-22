# rust.pkg.re

Public, declarative, curated Cargo sparse registries served at [rust.pkg.re](https://rust.pkg.re/).

| Registry | Sparse index | Scope | May depend on |
|---|---|---|---|
| `core` | `sparse+https://rust.pkg.re/core/` | General approved Rust packages | `core` |
| `matrix` | `sparse+https://rust.pkg.re/matrix/` | Matrix/Ruma package family | `matrix`, `core` |
| `pkgre` | `sparse+https://rust.pkg.re/pkgre/` | pkg.re first-party tools | `pkgre`, `matrix`, `core` |

## Model

`registry/{core,matrix,pkgre}.toml` = complete human-edited desired state: fixed registry policy + exact crates.io mirror versions + approved first-party HTTPS Git tags. [`pkgre-indexer`](https://github.com/pkgre/pkgre) reconciles that state into canonical adjacent locks + content-addressed objects; validates package homes/dependency layers; renders the Pages site from scratch; verifies byte identity; rejects mutation, disappearance, or reactivation of any published identity.

Imported packages retain exact crates.io `.crate` bytes/checksums + source rows. First-party releases lock Git tag object + peeled commit + package path + Cargo version, require explicit curated-registry routing, and package twice byte-identically under pinned Cargo.

Removal = retain package key but remove version/tag from the human list → lock transitions `active→removed` irreversibly; source row remains; rendered row becomes yanked; unshared archive is deleted and no longer served. Re-adding a removed identity fails closed.

Approval means an exact artifact was admitted; not a warranty that package code is benign, correct, or maintained. Builds should remain isolated because approved build scripts/procedural macros execute code.

## Consumer configuration

```toml
[registries]
core = { index = "sparse+https://rust.pkg.re/core/" }
matrix = { index = "sparse+https://rust.pkg.re/matrix/" }
pkgre = { index = "sparse+https://rust.pkg.re/pkgre/" }

[registry]
default = "core"

[source.crates-io]
replace-with = "disabled-crates-io"

[source.disabled-crates-io]
directory = "vendor/empty"
```

Every manifest dependency should set `registry = "core"`, `"matrix"`, or `"pkgre"`; commit `vendor/empty/.gitkeep`; commit the lockfile; use `cargo build --locked` or `--frozen`. Cargo has no universal registry allowlist; committed row validation + explicit routing remain part of the security boundary.

## Repository

| Path | Authority/purpose |
|---|---|
| `registry/<name>.toml` | Human authority: registry policy, exact mirrored versions, approved Git repo/tags; empty list permanently reserves/removes a name |
| `registry/<name>.lock` | Generated authority: permanent name/source class, lifecycle, archive/source-row/routed-row hashes, immutable Git provenance |
| `registry/objects/crates/<sha256>.crate` | Exact active content-addressed archives |
| `registry/objects/rows/<sha256>.json` | Exact retained un-routed source rows, including removed identities |

Curator schema/workflows/security documentation: [pkgre/pkgre](https://github.com/pkgre/pkgre).

## License

Curator-authored catalog metadata + repository documentation: Apache-2.0. Retained third-party package archives: each package's own license; inclusion does not relicense them.
