#!/usr/bin/env python3
"""Check a random sample of live DataCite records with the toolkit's validators.

Fetches randomly chosen findable DOIs from the public DataCite REST API, then for
each record runs the JSON Schema, the JSON-to-RDF converter and the SHACL shapes,
and prints a summary of the problems found, grouped by kind. Use it to see how
the validators behave on real data; the sample differs on every run.

Every problem reported should be a real problem in the record. If a record that
follows the DataCite rules is rejected, that is a bug in the toolkit: please
report it with the DOI.

Usage:
    python3 validation-and-conversion/scripts/check_live_sample.py [--size 300] [--save sample.json]
"""

import argparse
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

import jsonschema
import pyshacl
import rdflib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from datacite_to_rdf import DEFAULT_CONTEXT, load_context, to_graph  # noqa: E402

API = "https://api.datacite.org/dois?random=true&state=findable&affiliation=true&publisher=true&page%5Bsize%5D={size}"
SCHEMA = ROOT / "validation-and-conversion" / "schemas" / "schema-profiles" / "datacite.schema.json"


def fetch(size):
    records = []
    while len(records) < size:
        batch = min(1000, size - len(records))
        with urllib.request.urlopen(API.format(size=batch), timeout=120) as response:
            records += json.load(response)["data"]
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--size", type=int, default=300, help="number of records to fetch (default 300)")
    parser.add_argument("--save", help="also save the fetched records to this JSON file")
    args = parser.parse_args()

    current = json.loads((ROOT / "rdf-vocabulary-staging" / "manifest" / "datacite-current.json").read_text(
        encoding="utf-8"))["currentVersion"]
    shapes = rdflib.Graph().parse(ROOT / "validation-and-conversion" / "shapes" / f"datacite-{current}.shacl.ttl")
    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    context = load_context(DEFAULT_CONTEXT)

    records = fetch(args.size)
    if args.save:
        Path(args.save).write_text(json.dumps(records, indent=1), encoding="utf-8")

    schema_problems, rdf_problems, warnings, failures = Counter(), Counter(), Counter(), []
    examples = {}
    flagged = set()
    for record in records:
        doi = record["id"]
        for error in validator.iter_errors({"data": record}):
            path = "/".join("[]" if isinstance(p, int) else str(p) for p in list(error.absolute_path)[2:])
            key = f"{path or '(record)'}: {error.message[:90]}"
            schema_problems[key] += 1
            examples.setdefault(key, doi)
            flagged.add(doi)
        found = []
        try:
            graph = to_graph(record["attributes"], context, warnings=found)
        except Exception as error:  # report any converter failure; do not stop the run
            failures.append(f"{doi}: {error!r}")
            continue
        for warning in found:
            warnings[warning.split(": ", 1)[1]] += 1
        conforms, report, _ = pyshacl.validate(graph, shacl_graph=shapes)
        if not conforms:
            flagged.add(doi)
            for message in set(report.objects(None, rdflib.SH.resultMessage)):
                rdf_problems[str(message)[:110]] += 1
                examples.setdefault(str(message)[:110], doi)

    print(f"{len(records)} random findable DOIs; {len(flagged)} with at least one problem; "
          f"{len(failures)} converter failures.\n")
    for title, counter in (("JSON Schema", schema_problems), ("SHACL, after conversion", rdf_problems),
                           ("Converter warnings", warnings)):
        print(f"{title}:")
        for key, count in counter.most_common() or [("none", 0)]:
            print(f"  {count:4}  {key}" + (f"   e.g. {examples[key]}" if key in examples else ""))
        print()
    for failure in failures:
        print("Converter failure:", failure)
    return 0


if __name__ == "__main__":
    sys.exit(main())
