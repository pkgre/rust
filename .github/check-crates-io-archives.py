#!/usr/bin/env python3
"""Require the crates.io archives of the mirrors a catalog change adds.

The catalog retains the archive of every mirror it admits, and the serving origin delivers
that retained archive; nothing else proves that it is the archive crates.io serves under
that name and version. This checks that every crates.io mirror identity the change adds
has, on static.crates.io, an archive with the locked checksum.

usage: check-crates-io-archives.py <accepted-catalog> <candidate-catalog>
"""

import hashlib
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

DOWNLOAD = "https://static.crates.io/crates/{name}/{name}-{version}.crate"
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
    """Yields (lock file, name, version, crate-sha256) of every locked crates.io package."""
    for lock in lock_files(catalog):
        with lock.open("rb") as handle:
            document = tomllib.load(handle)
        for package in document.get("packages", []):
            if package.get("source", {}).get("kind") != "crates-io":
                continue
            yield lock.name, package["name"], package["version"], package["crate-sha256"]


def added_mirrors(accepted, candidate):
    """Yields the crates.io identities the candidate locks and the accepted catalog does not."""
    known = {(lock, name, version) for lock, name, version, _ in locked_crates_io(accepted)}
    for identity in locked_crates_io(candidate):
        lock, name, version, sha256 = identity
        if (lock, name, version) not in known:
            yield lock, name, version, sha256


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


def main(arguments):
    if len(arguments) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    accepted, candidate = arguments[1:]
    added = list(added_mirrors(accepted, candidate))
    if not added:
        print("the change adds no crates.io mirror; no archive is downloaded")
        return 0
    failed = 0
    for lock, name, version, expected in added:
        identity = f"{name} {version} ({lock})"
        try:
            actual = download_digest(name, version)
        except RuntimeError as error:
            print(f"{identity}: FAILED: {error}", file=sys.stderr)
            failed += 1
            continue
        if actual != expected:
            print(
                f"{identity}: FAILED: static.crates.io serves {actual}, "
                f"the catalog locks {expected}",
                file=sys.stderr,
            )
            failed += 1
            continue
        print(f"{identity}: checksum matches")
    print(f"{len(added)} added crates.io archives, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
