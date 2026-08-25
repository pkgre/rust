# rust.pkg.re

Public declarative curated Cargo sparse registry served at [rust.pkg.re](https://rust.pkg.re/).

## Production topology

| Cargo alias | Catalog alias | Sparse index | Sources | Archive download |
|---|---|---|---|---|
| `pkgre` | `main` | `sparse+https://rust.pkg.re/` | crates.io mirrors + first-party/fork Git tags | `https://dl.rust.pkg.re/v1/main/{crate}/{version}/{sha256-checksum}` |

Cargo aliases are consumer-local; `main` is the catalog/index identity. Schema 4 remains multi-registry capable:an additional catalog registry such as `staging` renders below `https://rust.pkg.re/staging/`, receives its own categories/lock/routes, and does not move existing `main` identities.

Cargo exposes one `dl` URL per registry. Generated `registry/downloads.json` binds every active `(registry,name,version,sha256)` identity to its locked `crates-io` or `git-tag` source. The stateless router derives only hardcoded source-specific destinations:crates.io identities redirect to their original static archive; Git-tag identities redirect to their active content-addressed publication archive. No crates.io `.crate` files are committed.

## Categories

Categories are catalog policy identities, not Cargo registry aliases. Every package name has one permanent `<registry>/<category>` home; each category declares the complete set of category identities its packages may depend on. Source is version-specific:a package name may retain mirrored versions and use later Git-published fork versions, but each `name + version` identity has one immutable checksum.

| Category | Scope | Exact `may-depend-on` |
|---|---|---|
| `main/general` | General crates.io packages | `main/general` |
| `main/acp` | Agent Client Protocol packages | `main/acp`, `main/general` |
| `main/filesystem` | Filesystem notification packages | `main/filesystem`, `main/general` |
| `main/matrix` | Matrix/Ruma package family | `main/general`, `main/matrix` |
| `main/mcp` | Model Context Protocol packages | `main/general`, `main/mcp`, `main/sse` |
| `main/pkgre` | pkg.re first-party packages + forks | `main/general`, `main/pkgre` |
| `main/sse` | Server-sent event packages | `main/general`, `main/sse` |
| `main/terminal` | Terminal/PTY packages | `main/general`, `main/terminal` |
| `main/yaml` | YAML packages | `main/general`, `main/yaml` |

Small categories are inline under `[categories.<name>]` in `registry/<registry>.toml`; large categories use `file = "categories/<registry>/<category>.toml"`. An external file contains that category's `schema`, `may-depend-on`, and `mirror` or `publish` declarations.

## Model

`registry/main.toml` + external category files = complete human-edited desired state:fixed registry/category policy + exact crates.io mirror versions + approved first-party HTTPS Git tags. New mirror identities/versions enter an established catalog only through evidence-bound batch admission with `update-plan`/`update-inspect`/`update-apply`; direct `lock` admission is rejected. `lock` handles initial bootstrap, empty name reservations, removals, and Git publication tags; reconciles permitted state into canonical adjacent locks + content-addressed objects + `downloads.json`; validates permanent package homes, category dependency edges, source integrity, and router policy; renders the Pages site from scratch; verifies byte identity; rejects mutation, disappearance, reactivation, or ambiguous cross-registry dependency routing.

`update-plan` writes its review template outside `registry/`; it does not create an intermediate repository state or PR. After optional evidence edits, `update-apply` atomically installs the exact manifest, generated evidence lock, declarations, registry locks, row objects, and router catalog together; one batch therefore has one fully applied registry PR. CI rejects an unpaired, stale, orphaned, or catalog-unbound admission through `check`, then runs `lock` and rejects any resulting tracked or untracked `registry/` change.

Imported packages retain exact crates.io checksums + source rows. Git releases lock tag object + peeled commit + package path + Cargo version, require explicit curated-registry dependency routing, and package twice byte-identically under pinned Cargo.

Removal = retain package key but remove version/tag from the human list → lock transitions `active→removed` irreversibly; source row remains; rendered row becomes yanked; an unshared Git archive is deleted and no longer served. Re-adding a removed identity fails closed.

Approval means an exact artifact was admitted; not a warranty that package code is benign, correct, or maintained. Builds should remain isolated because approved build scripts/procedural macros execute code.

## Consumer configuration

Project `.cargo/config.toml`:

```toml
[registries.pkgre]
index = "sparse+https://rust.pkg.re/"

[registry]
default = "pkgre"

[source.crates-io]
replace-with = "disabled-crates-io"

[source.disabled-crates-io]
directory = ".cargo/disabled-crates-io"
```

Create + commit `.cargo/disabled-crates-io/`. Every manifest dependency should set `registry = "pkgre"`; commit the lockfile; use `cargo build --locked` or `--frozen`. Do not use `source.crates-io.replace-with = "pkgre"`:source replacement is local configuration and Cargo can reinterpret crates.io identities when another user lacks it. Explicit `registry = "pkgre"` records the root sparse source in `Cargo.lock` and fails closed when a clone omits the alias configuration.

## Repository

| Path | Authority/purpose |
|---|---|
| `registry/<registry>.toml` | Human authority:registry policy + inline category declarations |
| `registry/categories/<registry>/<category>.toml` | Human authority:one large external category declaration |
| `registry/<registry>.lock` | Generated authority:permanent category homes, lifecycle, archive/source-row/routed-row hashes, immutable source provenance, optional admission-batch hash |
| `registry/downloads.json` | Generated canonical router projection:one source route per active checksum-bound package identity |
| `registry/admissions/<batch>.toml` | Human authority:canonical exact package/version/category requests + optional typed review evidence |
| `registry/admissions/<batch>.lock` | Generated evidence:policy/API/archive/source facts for the complete batch; every admitted package binds its SHA-256 |
| `registry/objects/crates/<sha256>.crate` | Exact active Git publication archives; mirror archives are checksum-verified then discarded |
| `registry/objects/rows/<sha256>.json` | Exact retained unrouted source rows, including removed identities |

Curator schema/workflow/security documentation:[`pkgre/pkgre`](https://github.com/pkgre/pkgre).

## License

Curator-authored catalog metadata + repository documentation:Apache-2.0. Retained first-party package archives:each package's own license; inclusion does not relicense them.
