#!/usr/bin/env python3
"""Require the crates.io archives and index rows of the mirrors a catalog change adds.

The catalog retains the archive of every mirror it admits, and the serving origin delivers
that retained archive; nothing else proves that it is the archive crates.io serves under
that name and version. The catalog likewise retains crates.io's sparse-index line for that
version as the mirror's source row, and serves that row as the index row; nothing else
proves that the dependencies, features and metadata it publishes are crates.io's own. This
checks that every crates.io mirror identity the change adds has, on static.crates.io, an
archive with the locked checksum, and that the SHA-256 of crates.io's index line for that
version, with a trailing newline, is the locked source-row checksum.

usage: check-crates-io-archives.py <accepted-catalog> <candidate-catalog>
"""

import hashlib
import json
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

DOWNLOAD = "https://static.crates.io/crates/{name}/{name}-{version}.crate"
INDEX = "https://index.crates.io/{path}"
ROWS = "objects/rows/{sha256}.json"
ATTEMPTS = 3
PAUSE_SECONDS = 2
CHUNK = 1 << 16


def lock_files(catalog):
    """Returns the generated lock files of one catalog, refusing a directory that holds none."""
    locks = sorted(Path(catalog).glob("*.lock"))
    if not locks:
        raise SystemExit(f"{catalog}: no *.lock file, so it is not a catalog")
    return locks


def locked_crates_io(catalog):
    """Yields (lock file, name, version, crate-sha256, source-row-sha256) of every locked
    crates.io package."""
    for lock in lock_files(catalog):
        with lock.open("rb") as handle:
            document = tomllib.load(handle)
        for package in document.get("packages", []):
            if package.get("source", {}).get("kind") != "crates-io":
                continue
            yield (
                lock.name,
                package["name"],
                package["version"],
                package["crate-sha256"],
                package["source-row-sha256"],
            )


def added_mirrors(accepted, candidate):
    """Yields the crates.io identities the candidate locks and the accepted catalog does not."""
    known = {(lock, name, version) for lock, name, version, _, _ in locked_crates_io(accepted)}
    for identity in locked_crates_io(candidate):
        lock, name, version, _, _ = identity
        if (lock, name, version) not in known:
            yield identity


def download_digest(name, version):
    """Returns the SHA-256 of one crate's archive, trying a few times before giving up."""
    url = DOWNLOAD.format(name=name, version=version)
    failure = None
    for attempt in range(1, ATTEMPTS + 1):
        digest = hashlib.sha256()
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                for chunk in iter(lambda: response.read(CHUNK), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        except (urllib.error.URLError, OSError) as error:
            failure = error
            print(f"{url}: attempt {attempt} of {ATTEMPTS} failed: {error}", file=sys.stderr)
            if attempt < ATTEMPTS:
                time.sleep(PAUSE_SECONDS)
    raise RuntimeError(f"cannot download {url}: {failure}")


def index_path(name):
    """Returns the sparse-index path of one crate, from its lowercased name."""
    name = name.lower()
    if len(name) == 1:
        return f"1/{name}"
    if len(name) == 2:
        return f"2/{name}"
    if len(name) == 3:
        return f"3/{name[0]}/{name}"
    return f"{name[:2]}/{name[2:4]}/{name}"


def fetch(url):
    """Returns the whole body of one URL, trying a few times before giving up."""
    failure = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return response.read()
        except (urllib.error.URLError, OSError) as error:
            failure = error
            print(f"{url}: attempt {attempt} of {ATTEMPTS} failed: {error}", file=sys.stderr)
            if attempt < ATTEMPTS:
                time.sleep(PAUSE_SECONDS)
    raise RuntimeError(f"cannot fetch {url}: {failure}")


def index_lines(name, cache):
    """Returns one crate's index lines, reading its index file once per run and caching them.

    The cache maps a crate's index URL to its lines, or to the failure reading them hit, so
    that a later identity of the same crate fails the same way without another try.
    """
    url = INDEX.format(path=index_path(name))
    if url not in cache:
        try:
            cache[url] = fetch(url).split(b"\n")
        except RuntimeError as error:
            cache[url] = error
    lines = cache[url]
    if isinstance(lines, RuntimeError):
        raise lines
    return [line for line in lines if line]


def source_row(name, version, cache):
    """Returns crates.io's index line for one version, exactly as served, without a newline."""
    rows = []
    for line in index_lines(name, cache):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"{name}: cannot parse an index line: {error}")
        if row.get("vers") == version:
            rows.append(line)
    if not rows:
        raise RuntimeError(f"crates.io's index has no line for {name} {version}")
    if len(rows) > 1:
        raise RuntimeError(f"crates.io's index has {len(rows)} lines for {name} {version}")
    return rows[0]


def differing_keys(stored, served):
    """Returns the top-level keys whose values differ between two parsed index rows."""
    return sorted(
        key for key in set(stored) | set(served) if stored.get(key) != served.get(key)
    )


def row_failure(catalog, name, version, expected, served):
    """Names why the source row a catalog locks differs from the line crates.io serves."""
    digest = hashlib.sha256(served + b"\n").hexdigest()
    message = f"crates.io serves {digest}, the catalog locks {expected}"
    stored_path = Path(catalog) / ROWS.format(sha256=expected)
    try:
        stored = json.loads(stored_path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        return f"{message}; {stored_path}: {error}"
    keys = differing_keys(stored, json.loads(served))
    if keys == ["yanked"]:
        return f"{message}; crates.io yanked {name} {version} since it was admitted"
    if not keys:
        return f"{message}; the stored row holds different bytes of the same JSON"
    return f"{message}; keys differ: {', '.join(keys)}"


def main(arguments):
    if len(arguments) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    accepted, candidate = arguments[1:]
    added = list(added_mirrors(accepted, candidate))
    if not added:
        print("the change adds no crates.io mirror; no archive or index row is read")
        return 0
    failed = 0
    index_files = {}
    for lock, name, version, expected_archive, expected_row in added:
        identity = f"{name} {version} ({lock})"
        failures = []
        try:
            archive = download_digest(name, version)
        except RuntimeError as error:
            failures.append(str(error))
        else:
            if archive != expected_archive:
                failures.append(
                    f"static.crates.io serves {archive}, "
                    f"the catalog locks {expected_archive}"
                )
        try:
            served = source_row(name, version, index_files)
        except RuntimeError as error:
            failures.append(f"index row: {error}")
        else:
            if hashlib.sha256(served + b"\n").hexdigest() != expected_row:
                failures.append(
                    f"index row: {row_failure(candidate, name, version, expected_row, served)}"
                )
        for failure in failures:
            print(f"{identity}: FAILED: {failure}", file=sys.stderr)
        if failures:
            failed += 1
        else:
            print(f"{identity}: archive checksum and source row match")
    print(f"{len(added)} added crates.io mirrors, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
