# rust.pkg.re

Public declarative curated Cargo sparse registry served at [rust.pkg.re](https://rust.pkg.re/).

## Production topology

| Cargo alias | Catalog alias | Sparse index | Sources | Archive download |
|---|---|---|---|---|
| `pkgre` | `main` | `sparse+https://rust.pkg.re/` | crates.io mirrors + first-party/fork Git tags | `https://rust.pkg.re/v1/main/{crate}/{version}/{sha256-checksum}` |

Cargo aliases are consumer-local; `main` is the catalog/index identity. Schema 5 remains multi-registry capable:an additional catalog registry such as `staging` renders below `https://rust.pkg.re/r/staging/`, receives its own categories/lock/routes, and does not move existing `main` identities. The serving gate `check-transition` rejects a candidate that adds or removes a registry, so a new alias needs a fresh accepted baseline before the service publishes it.

Cargo exposes one `dl` URL per registry. `main` declares `audience = "public"` and `delivery = "retained"`:every `.crate` archive of an active identity, crates.io mirrors and Git tags alike, is committed once as `registry/objects/crates/<sha256>.crate`. Generated `registry/downloads.json` binds every `(registry,name,version,sha256)` identity to its retained archive. The serving origin `pkgre-rust-serve` answers from a validated in-memory projection of an accepted commit of this repository:the `/v1` route redirects to or serves the content-addressed body. It publishes a new commit of `main` only when `check-transition` accepts it as a successor of the last accepted commit, and otherwise keeps serving the last accepted snapshot.

## Categories

Categories are catalog policy identities, not Cargo registry aliases. Every package name has one permanent `<registry>/<category>` home; each category declares the complete set of category identities its packages may depend on. Source is version-specific:a package name may retain mirrored versions and use later Git-published fork versions, but each `name + version` identity has one immutable checksum.

| Category | Scope | Exact `may-depend-on` |
|---|---|---|
| `main/general` | General crates.io packages | `main/general` |
| `main/acp` | Agent Client Protocol packages | `main/acp`, `main/general` |
| `main/ethereum` | Ethereum packages | `main/ethereum`, `main/general` |
| `main/filesystem` | Filesystem notification packages | `main/filesystem`, `main/general` |
| `main/matrix` | Matrix/Ruma package family | `main/general`, `main/matrix` |
| `main/mcp` | Model Context Protocol packages | `main/general`, `main/mcp`, `main/sse` |
| `main/pkgre` | pkg.re first-party packages + forks | `main/general`, `main/pkgre` |
| `main/sse` | Server-sent event packages | `main/general`, `main/sse` |
| `main/terminal` | Terminal/PTY packages | `main/general`, `main/terminal` |
| `main/yaml` | YAML packages | `main/general`, `main/yaml` |

Small categories are inline under `[categories.<name>]` in `registry/<registry>.toml`; large categories use `file = "categories/<registry>/<category>.toml"`. An external file contains that category's `schema`, `may-depend-on`, and `mirror` or `publish` declarations.

## Model

`registry/main.toml` + external category files = complete human-edited desired state:fixed registry/category policy + exact crates.io mirror versions + approved first-party HTTPS Git tags. New mirror identities/versions enter an established catalog only through evidence-bound batch admission with `update-plan`/`update-inspect`/`update-apply`; direct `lock` admission is rejected. `lock` handles initial bootstrap, empty name reservations, removals, and Git publication tags; reconciles permitted state into canonical adjacent locks + content-addressed objects + `downloads.json`; validates permanent package homes, category dependency edges, source integrity, and router policy; verifies the staged objects + routed rows, test-renders the staged copy, and installs it atomically; rejects mutation, disappearance, reactivation, or ambiguous cross-registry dependency routing.

`update-plan` writes its review template outside `registry/`; it does not create an intermediate repository state or PR. After optional evidence edits, `update-apply` atomically installs the exact manifest, generated evidence lock, declarations, registry locks, row objects, and router catalog together; one batch therefore has one fully applied registry PR. CI rejects an unpaired, stale, orphaned, or catalog-unbound admission through `check`, then runs `lock` and rejects any resulting tracked or untracked `registry/` change.

CI checks the change the way the serving origin does, from the accepted state, the first parent of the change: `check-transition` accepts only a successor of that state; `check-serve --delivery=body` builds the snapshot the origin builds, with an empty archive store, so every mirror body must come from the catalog itself; `reproduce-git-tags` re-fetches and re-packages the Git-tag identities the change adds; and the crates.io archive of every mirror the change adds must match its locked SHA-256. It also renders and verifies the site, and verifies the change monotonic against the rendered accepted state.

Imported packages retain exact crates.io checksums + source rows. Git releases lock tag object + peeled commit + package path + Cargo version, require explicit curated-registry dependency routing, and package twice byte-identically under pinned Cargo.

Removal = retain package key but remove version/tag from the human list → lock transitions `active→removed` irreversibly; source row and route remain; rendered row becomes yanked; an unshared retained archive is deleted and no longer served. Re-adding a removed identity fails closed. The serving gate `check-transition` accepts an `active→removed` change, but the body-delivery snapshot of a removal whose archive was deleted cannot be built, so `check-serve` in CI refuses such a removal, as the serving origin would.

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
| `registry/downloads.json` | Generated canonical route projection:one checksum-bound route per package identity, to its retained archive |
| `registry/admissions/<batch>.toml` | Human authority:canonical exact package/version/category requests + optional typed review evidence |
| `registry/admissions/<batch>.lock` | Generated evidence:policy/API/archive/source facts for the complete batch; every admitted package binds its SHA-256 |
| `registry/objects/crates/<sha256>.crate` | Exact retained archives of active identities:Git publications and, under `delivery = "retained"`, checksum-verified crates.io mirrors |
| `registry/objects/rows/<sha256>.json` | Exact retained unrouted source rows, including removed identities |

Curator schema/workflow/security documentation:[`pkgre/pkgre`](https://github.com/pkgre/pkgre).

## Self-publishing

`self-publish/` declares which releases of a self-publishing repository also reach crates.io, and under which names. It sits beside `registry/`, which stays the reconciler's exclusive state, and holds exactly these two files:

| Path | Authority/purpose |
|---|---|
| `self-publish/crates-io.toml` | Human authority:crates.io owners, the self-publishing repositories and their release-tag prefixes, name mappings, abandoned versions |
| `self-publish/crates-io.lock` | Generated authority:one entry per crate version released to crates.io, with its crates.io name, both archive checksums, and the release tag and commit |

A release tag `rust/vX.Y.Z` of `pkgre/pkgre` publishes each crate whose `publish` is `["pkgre"]` at that commit;`pkgre-rust` reaches crates.io as `pkgre-pkgs-pkgre-rust` unless `[names]` gives another name. Only `pkgre-rust self-publish-lock` writes the lock, and no one edits it by hand:a crates.io version cannot be replaced, so an entry is permanent. CI runs `pkgre-rust self-publish-check` against the accepted state of the change, and rejects any `self-publish/` change that a `pkgre-rust self-publish-lock` run would produce. The validate job's registry checks read the same accepted state, and both jobs derive it as the first parent of the change and pin the same tooling revision.

Formats, name rules, the derivation and the upload routine:[`docs/self-publish.md`](https://github.com/pkgre/pkgre/blob/main/docs/self-publish.md).

## License

Curator-authored catalog metadata + repository documentation:Apache-2.0. Retained first-party package archives:each package's own license; inclusion does not relicense them.
