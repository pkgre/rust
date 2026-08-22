# rust.pkg.re

Public, declarative, curated Cargo sparse registries served at [rust.pkg.re](https://rust.pkg.re/).

| Registry | Sparse index | Scope | May depend on |
|---|---|---|---|
| `core` | `sparse+https://rust.pkg.re/core/` | General approved Rust packages | `core` |
| `matrix` | `sparse+https://rust.pkg.re/matrix/` | Matrix/Ruma package family | `matrix`, `core` |
| `pkgre` | `sparse+https://rust.pkg.re/pkgre/` | pkg.re first-party tools | `pkgre`, `matrix`, `core` |

## Model

`registry/` is the complete desired state: explicit package homes, exact approved versions, immutable source evidence, exact upstream sparse records, and content-addressed `.crate` bytes. [`pkgre-indexer`](https://github.com/pkgre/pkgre) validates policy, rewrites every dependency route, renders the Pages site from scratch, verifies byte identity, and rejects removal or mutation of published identities. Imported packages retain the exact crates.io archive bytes and checksum; first-party releases must reproduce from an HTTPS Git tag plus its full peeled commit under pinned Cargo.

Approval means an exact artifact was admitted to these registries; it is not a warranty that package code is benign, correct, or maintained. Builds should remain isolated because approved build scripts and procedural macros execute code.

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

Every manifest dependency should set `registry = "core"`, `"matrix"`, or `"pkgre"`; commit `vendor/empty/.gitkeep`; commit the lockfile; use `cargo build --locked` or `--frozen`. Cargo has no universal registry allowlist, so the committed row validator and explicit routing are part of the security boundary.

## Repository

| Path | Purpose |
|---|---|
| `registry/registries.toml` | Fixed topology, URLs, download template, packaging toolchain |
| `registry/homes.toml` | One explicit home for every approved or referenced package identity |
| `registry/approvals/` | Exact human-approved package identities and immutable origins |
| `registry/upstream/` | Exact un-routed crates.io sparse-row snapshots |
| `registry/archives/` | Exact content-addressed `.crate` bytes |
| `registry/artifacts.toml` | One-to-one map from approvals to retained artifacts |

Curator workflow/schema/security documentation: [pkgre/pkgre](https://github.com/pkgre/pkgre).

## License

Curator-authored catalog metadata and repository documentation: Apache-2.0. Retained third-party package archives: each package's own license; inclusion does not relicense them.
