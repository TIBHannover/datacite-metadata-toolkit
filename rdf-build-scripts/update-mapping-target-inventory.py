#!/usr/bin/env python3
"""Rebuild the offline target-term index from checksum-pinned official downloads.

Download the URLs in mappings/target-sources.json to their specified filenames
in a separate cache directory first. This command never accesses the network.
Changing a vocabulary snapshot requires reviewing and updating the source lock.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from rdflib import Graph, Literal, RDF, RDFS, URIRef


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "https://schema.org/"
OWL = "http://www.w3.org/2002/07/owl#"
SKOS = "http://www.w3.org/2004/02/skos/core#"


def build_inventory(source_lock, source_dir):
    if source_lock.get("version") != 1:
        raise ValueError("Unsupported target source lock version")
    terms = {}
    for key, source in sorted(source_lock["sources"].items()):
        source_file = source_dir / source["filename"]
        raw = source_file.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError(f"Checksum mismatch for {source_file}; review the source lock")
        if source["format"] == "wikidata-json":
            data = json.loads(raw)
            if "entities" not in data:
                raise ValueError(f"Missing entities in {source_file}")
            for identifier, entity in sorted(data["entities"].items()):
                if "missing" in entity:
                    continue
                label = entity.get("labels", {}).get("en", {}).get("value")
                if not label:
                    raise ValueError(f"Missing English label for {identifier}")
                terms[source["namespace"] + identifier] = {
                    "label": label,
                    "type": "http://wikiba.se/ontology#" + (
                        "Property" if identifier.startswith("P") else "Item"
                    ),
                    "source": key,
                }
            continue

        graph = Graph().parse(data=raw, format=source["format"])
        subjects = {
            subject for subject in graph.subjects(RDF.type, None)
            if isinstance(subject, URIRef) and str(subject).startswith(source["namespace"])
        }
        for subject in sorted(subjects):
            types = sorted(str(value) for value in graph.objects(subject, RDF.type))
            priority = [
                str(RDF.Property), OWL + "ObjectProperty", OWL + "DatatypeProperty",
                SCHEMA + "DataType", str(RDFS.Datatype), str(RDFS.Class),
                OWL + "Class", SKOS + "Concept",
            ]
            kind = next((value for value in priority if value in types), types[0])
            labels = list(graph.objects(subject, RDFS.label))
            label = next((str(value) for value in labels
                          if isinstance(value, Literal) and value.language == "en"), None)
            if label is None:
                label = str(sorted(labels, key=str)[0]) if labels else str(subject).rsplit("/", 1)[-1]
            term = {"label": label, "type": kind, "source": key}
            replacements = sorted(str(value) for value in graph.objects(
                subject, URIRef(SCHEMA + "supersededBy")))
            deprecated = any(value.toPython() is True for value in graph.objects(
                subject, URIRef(OWL + "deprecated")) if isinstance(value, Literal))
            if replacements or deprecated:
                term["deprecated"] = True
            if replacements:
                term["replaced_by"] = replacements
            terms[str(subject)] = term
    return {"version": 1, "sources": source_lock["sources"], "terms": dict(sorted(terms.items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--source-lock", type=Path, default=ROOT / "mappings/target-sources.json")
    parser.add_argument("--output", type=Path, default=ROOT / "mappings/target-vocabularies.json")
    parser.add_argument("--check", action="store_true", help="Fail if the committed index differs")
    args = parser.parse_args()
    try:
        inventory = build_inventory(json.loads(args.source_lock.read_text()), args.source_dir)
        rendered = json.dumps(inventory, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            if not args.output.exists() or args.output.read_text() != rendered:
                raise ValueError(f"Target inventory is stale: {args.output}")
        else:
            args.output.write_text(rendered)
        print(f"{'Checked' if args.check else 'Wrote'} {len(inventory['terms'])} target terms")
    except (OSError, ValueError, KeyError) as error:
        print(f"Target inventory error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
