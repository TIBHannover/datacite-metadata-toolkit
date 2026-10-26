#!/usr/bin/env python3
"""Fail if the files of an earlier, frozen release change.

Every version with a manifest in rdf-vocabulary-staging/manifest/ other than the
current one is frozen. Its files (dist/datacite-<version>.*, its OWL files,
manifest/datacite-<version>.json, context/fullcontext-<version>.jsonld and the
release matrix ending in that version) are recorded with their SHA-256 checksums
in rdf-build-scripts/frozen-releases.json.

Usage:
    python3 rdf-build-scripts/check-frozen-releases.py                     # check
    python3 rdf-build-scripts/check-frozen-releases.py --record <version>  # record

Record a version when a new version replaces it as current, or after a
deliberate, documented correction of a frozen file.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "rdf-vocabulary-staging"
RECORD = ROOT / "rdf-build-scripts" / "frozen-releases.json"


def current_version():
    return json.loads((STAGING / "manifest" / "datacite-current.json").read_text(encoding="utf-8"))["currentVersion"]


def versions():
    names = (p.name[len("datacite-"):-len(".json")] for p in (STAGING / "manifest").glob("datacite-*.json"))
    return sorted(v for v in names if v != "current")


def release_files(version):
    files = list((STAGING / "dist").glob(f"datacite-{version}.*")) + \
        list((STAGING / "dist").glob(f"datacite-{version}-owl*")) + \
        list((STAGING / "manifest").glob(f"release-matrix-*-{version}.json")) + \
        [STAGING / "manifest" / f"datacite-{version}.json", STAGING / "context" / f"fullcontext-{version}.jsonld"]
    return sorted({p.relative_to(ROOT).as_posix() for p in files if p.exists()})


def checksum(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--record", metavar="VERSION", help="record the current checksums of a frozen version")
    args = parser.parse_args()

    recorded = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}
    current = current_version()

    if args.record:
        if args.record == current:
            raise SystemExit(f"{args.record} is the current version; record it once a new version replaces it.")
        if args.record not in versions():
            raise SystemExit(f"No manifest for version {args.record}")
        recorded[args.record] = {name: checksum(name) for name in release_files(args.record)}
        RECORD.write_text(json.dumps(dict(sorted(recorded.items())), indent=2) + "\n", encoding="utf-8")
        print(f"Recorded {len(recorded[args.record])} files of frozen release {args.record}")
        return 0

    problems = []
    for version in versions():
        if version == current:
            continue
        if version not in recorded:
            problems.append(f"{version} is frozen but not recorded; run --record {version}")
            continue
        files = release_files(version)
        for name in sorted(set(recorded[version]) | set(files)):
            if name not in files:
                problems.append(f"{name} is missing")
            elif name not in recorded[version]:
                problems.append(f"{name} is new in frozen release {version}")
            elif checksum(name) != recorded[version][name]:
                problems.append(f"{name} has changed")
    if problems:
        print("Frozen releases changed:\n  " + "\n  ".join(problems), file=sys.stderr)
        print("If a change is deliberate, document it and run --record <version>.", file=sys.stderr)
        return 1
    print(f"Frozen releases unchanged: {', '.join(v for v in versions() if v != current)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
