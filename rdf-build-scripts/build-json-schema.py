#!/usr/bin/env python3
"""Write the DataCite JSON Schema for the current DataCite version from the DataCite vocabularies.

The schema lives in validation-and-conversion/schemas/schema-profiles/:

- datacite-<version>.schema.json, one per DataCite schema version, for example
  datacite-4.7.schema.json. The version comes from
  rdf-vocabulary-staging/manifest/datacite-current.json ("4.7-r2" is DataCite 4.7).
  When a new DataCite version becomes current, its file is created from the
  newest existing one, and the files of earlier versions are left unchanged.
- datacite.schema.json, which always equals the current version's file apart
  from its $id. Link to this one when you want the newest rules.

Each controlled list ($defs/resourceTypeGeneral, $defs/relationType, ...) is the
set of term notations in rdf-vocabulary-staging/vocab/<list>/, the spelling the
REST API uses ("Crossref Funder ID", not "CrossrefFunderID"). The script also
writes the version into the $id, title and descriptions. The rules themselves
are maintained by hand; after a new DataCite release, review them against the
release notes.

Usage:
    python3 rdf-build-scripts/build-json-schema.py          # write the files
    python3 rdf-build-scripts/build-json-schema.py --check  # fail if they are out of date
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "rdf-vocabulary-staging"
VOCAB = STAGING / "vocab"
PROFILES = ROOT / "validation-and-conversion" / "schemas" / "schema-profiles"
CURRENT = PROFILES / "datacite.schema.json"
ID_BASE = "https://w3id.org/tib/datacite/schema-profiles/"
LISTS = ["resourceTypeGeneral", "titleType", "nameType", "contributorType", "dateType", "relatedIdentifierType",
         "relationType", "descriptionType", "funderIdentifierType", "numberType"]
VERSIONED = re.compile(r"^datacite-(\d+(?:\.\d+)*)\.schema\.json$")


def datacite_version():
    """The DataCite schema version of the current modelling revision: "4.7-r2" -> "4.7"."""
    pointer = json.loads((STAGING / "manifest" / "datacite-current.json").read_text(encoding="utf-8"))
    return pointer["currentVersion"].split("-r", 1)[0]


def version_key(version):
    return tuple(int(part) for part in version.split("."))


def versioned_path(version):
    return PROFILES / f"datacite-{version}.schema.json"


def starting_point(version):
    """The current version's file, or, for a new version, the newest earlier one."""
    path = versioned_path(version)
    if path.exists():
        return path
    earlier = sorted((m.group(1) for m in map(VERSIONED.match, (p.name for p in PROFILES.iterdir())) if m),
                     key=version_key)
    if not earlier:
        raise SystemExit(f"No datacite-<version>.schema.json found in {PROFILES}")
    return versioned_path(earlier[-1])


def notations(scheme):
    values = []
    for path in sorted((VOCAB / scheme).glob("*.jsonld")):
        if path.stem in (scheme, "context"):
            continue
        term = json.loads(path.read_text(encoding="utf-8"))
        values.append(term.get("notation") or path.stem)
    if not values:
        raise SystemExit(f"No terms found in {VOCAB / scheme}")
    return sorted(values, key=str.lower)


def build(version):
    schema = json.loads(starting_point(version).read_text(encoding="utf-8"))
    schema["$id"] = f"{ID_BASE}datacite-{version}.schema.json"
    schema["title"] = f"DataCite Metadata Schema {version} – REST API JSON"
    for holder in (schema, schema["$defs"]["attributes"]):
        holder["description"] = re.sub(r"DataCite Metadata Schema \d+(?:\.\d+)*",
                                       f"DataCite Metadata Schema {version}", holder["description"])
    for name in LISTS:
        schema["$defs"][name]["description"] = (
            f"DataCite {version} controlled list {name}. Generated from rdf-vocabulary-staging/vocab/{name}/ "
            "by rdf-build-scripts/build-json-schema.py.")
        schema["$defs"][name]["enum"] = notations(name)
    current = dict(schema, **{"$id": f"{ID_BASE}{CURRENT.name}"})
    return {versioned_path(version): schema, CURRENT: current}


def text(schema):
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if the schema files are out of date")
    args = parser.parse_args()

    outputs = build(datacite_version())
    stale = [path for path, schema in outputs.items()
             if not path.exists() or path.read_text(encoding="utf-8") != text(schema)]
    if args.check:
        if stale:
            names = ", ".join(str(p.relative_to(ROOT)) for p in stale)
            print(f"Out of date: {names}; run: python3 rdf-build-scripts/build-json-schema.py", file=sys.stderr)
            return 1
        print("JSON Schema files match the vocabularies and the current version.")
        return 0
    for path, schema in outputs.items():
        path.write_text(text(schema), encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
