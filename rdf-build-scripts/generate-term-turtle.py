#!/usr/bin/env python3
"""Write X.ttl next to every term X.jsonld in a namespace bundle.

Each Turtle file is re-parsed and must contain exactly the same triples as its
JSON-LD source, so a conversion error fails the build instead of shipping.
"""

import argparse
import sys
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.compare import isomorphic

GROUPS = ("class", "property", "vocab")
PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dcterms": "http://purl.org/dc/terms/",
    "schema": "https://schema.org/",
}


def term_files(bundle):
    for group in GROUPS:
        for path in sorted((bundle / group).rglob("*.jsonld")):
            if path.name != "context.jsonld":
                yield path


def convert(path):
    # The base lets relative contexts such as ./context.jsonld load from disk.
    source = Graph()
    source.parse(path, format="json-ld", base=path.resolve().as_uri())
    if not source:
        raise ValueError("no triples")
    local = [str(node) for triple in source for node in triple
             if isinstance(node, URIRef) and str(node).startswith("file:")]
    if local:
        raise ValueError(f"relative IRI resolved to a local file: {local[0]}")

    # Copy into a graph with fixed prefixes; JSON-LD context prefixes are not reused.
    output = Graph(bind_namespaces="none")
    for prefix, namespace in PREFIXES.items():
        output.bind(prefix, namespace)
    for triple in source:
        output.add(triple)
    text = output.serialize(format="turtle")

    check = Graph()
    check.parse(data=text, format="turtle")
    if not isomorphic(source, check):
        raise ValueError("Turtle triples differ from JSON-LD")
    path.with_suffix(".ttl").write_text(text, encoding="utf-8")
    return len(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="namespace bundle directory, e.g. production-namespace")
    args = parser.parse_args()
    files = triples = 0
    failures = []
    for path in term_files(args.bundle):
        try:
            triples += convert(path)
            files += 1
        except Exception as error:  # report every failing term, then fail
            failures.append(f"{path}: {error}")
    for failure in failures:
        print(f"Turtle conversion failed: {failure}", file=sys.stderr)
    print(f"Turtle: {files} term files, {triples} triples, {len(failures)} failures")
    return 1 if failures or not files else 0


if __name__ == "__main__":
    sys.exit(main())
