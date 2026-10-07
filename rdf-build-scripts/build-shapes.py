#!/usr/bin/env python3
"""Write the controlled-value section of the SHACL shapes from the DataCite vocabularies.

The current JSON-LD context names every property whose value is a controlled
term ("@type": "@vocab") and the vocabulary it uses. For each one, this script
writes a shape listing every term of that vocabulary with sh:in, so a misspelt
or undefined value (relationType "IsCitedby", resourceTypeGeneral "Datset")
fails validation. The section sits between the BEGIN and END GENERATED markers
in validation-and-conversion/shapes/datacite-4.7-r2.shacl.ttl; the rest of the
file is maintained by hand.

Usage:
    python3 rdf-build-scripts/build-shapes.py          # rewrite the section
    python3 rdf-build-scripts/build-shapes.py --check  # fail if it is out of date
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "rdf-vocabulary-staging"
SHAPES = ROOT / "validation-and-conversion" / "shapes" / "datacite-4.7-r2.shacl.ttl"
NAMESPACE = "https://w3id.org/tib/datacite/"
BEGIN = "# BEGIN GENERATED: controlled values (rdf-build-scripts/build-shapes.py; do not edit)"
END = "# END GENERATED: controlled values"


def controlled_properties():
    """(property name, vocabulary name) for every context term typed as a vocabulary term."""
    context = json.loads((STAGING / "context" / "fullcontext.jsonld").read_text(encoding="utf-8"))["@context"]
    found = {}
    for definition in context.values():
        if not isinstance(definition, dict) or definition.get("@type") != "@vocab":
            continue
        prop = definition["@id"].split(":", 1)[1]
        scheme = definition["@context"]["@vocab"].rstrip("/").rsplit("/", 1)[1]
        found[prop] = scheme
    return sorted(found.items())


def terms(scheme):
    folder = STAGING / "vocab" / scheme
    names = sorted(f.stem for f in folder.glob("*.jsonld") if f.stem not in (scheme, "context"))
    if not names:
        raise SystemExit(f"No terms found in {folder}")
    return names


def section():
    lines = [BEGIN, "#", "# One shape per controlled property: its value must be a term of the DataCite",
             "# vocabulary that the JSON-LD context assigns to it.", ""]
    for prop, scheme in controlled_properties():
        values = "\n".join(f"        <{NAMESPACE}vocab/{scheme}/{name}>" for name in terms(scheme))
        lines += [
            f"dcsh:{prop}Values",
            "    a sh:NodeShape ;",
            f"    sh:targetSubjectsOf dcp:{prop} ;",
            "    sh:property [",
            f"        sh:path dcp:{prop} ;",
            f"        sh:in (\n{values}\n        ) ;",
            f'        sh:message "{prop} must be a term of the DataCite {scheme} vocabulary." ;',
            "    ] .",
            "",
        ]
    lines.append(END)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if the generated section is out of date")
    args = parser.parse_args()

    text = SHAPES.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        raise SystemExit(f"{SHAPES} has no generated section markers")
    start = text.index(BEGIN)
    stop = text.index(END) + len(END)
    updated = text[:start] + section() + text[stop:]

    if args.check:
        if updated != text:
            print(f"{SHAPES.relative_to(ROOT)} is out of date; run: python3 rdf-build-scripts/build-shapes.py",
                  file=sys.stderr)
            return 1
        print("SHACL controlled-value shapes match the vocabularies.")
        return 0
    SHAPES.write_text(updated, encoding="utf-8")
    print(f"Wrote {SHAPES.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
