#!/usr/bin/env python3
"""Write the controlled lists of the DataCite JSON Schema from the DataCite vocabularies.

Each controlled list in validation-and-conversion/schemas/schema-profiles/
datacite-4.7.schema.json ($defs/resourceTypeGeneral, $defs/relationType, ...)
is the set of term notations in rdf-vocabulary-staging/vocab/<list>/, the
spelling the REST API uses ("Crossref Funder ID", not "CrossrefFunderID"). When a
DataCite release adds a term, the release tooling adds its vocabulary file and
this script carries it into the JSON Schema. The rest of the schema is
maintained by hand.

Usage:
    python3 rdf-build-scripts/build-json-schema.py          # rewrite the lists
    python3 rdf-build-scripts/build-json-schema.py --check  # fail if they are out of date
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOCAB = ROOT / "rdf-vocabulary-staging" / "vocab"
SCHEMA = ROOT / "validation-and-conversion" / "schemas" / "schema-profiles" / "datacite-4.7.schema.json"
LISTS = ["resourceTypeGeneral", "titleType", "nameType", "contributorType", "dateType", "relatedIdentifierType",
         "relationType", "descriptionType", "funderIdentifierType", "numberType"]


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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if the controlled lists are out of date")
    args = parser.parse_args()

    text = SCHEMA.read_text(encoding="utf-8")
    schema = json.loads(text)
    for name in LISTS:
        schema["$defs"][name]["enum"] = notations(name)
    updated = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if updated != text:
            print(f"{SCHEMA.relative_to(ROOT)} is out of date; run: python3 rdf-build-scripts/build-json-schema.py",
                  file=sys.stderr)
            return 1
        print("JSON Schema controlled lists match the vocabularies.")
        return 0
    SCHEMA.write_text(updated, encoding="utf-8")
    print(f"Wrote {SCHEMA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
