#!/usr/bin/env python3
"""Convert each example record before and after the structured-values change.

Writes before/<record>.ttl, after/<record>.ttl and RESULTS.md. "Before" is the
published context as of this prototype (context-before.jsonld) applied to the
record as-is; "after" is the prototype context plus prepare().
"""

import json
import sys
from pathlib import Path

import rdflib
from rdflib.compare import to_canonical_graph

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "validation-and-conversion" / "scripts"))

from datacite_to_rdf import load_context, record_attributes, to_graph  # noqa: E402

EXAMPLES = ROOT / "validation-and-conversion" / "examples"
# Output name -> record. The converter and records moved to validation-and-conversion/.
RECORDS = {"datacite-full-example": EXAMPLES / "record.json", "real-dataset": EXAMPLES / "real-dataset-dryad.json",
           "real-software": EXAMPLES / "real-software-zenodo.json"}
RDF_VALUE = rdflib.RDF.value
# Leaf keys that are derived citation formats or presentation-only.
SKIP_KEYS = {"schemaOrg", "bibtex", "citeproc", "ris", "lang", "doi"}
# JSON values the context deliberately translates to a vocabulary term.
ALIASES = {"Crossref Funder ID": "CrossrefFunderID"}
# (list, key holding the text, qualifier key) pairs whose link must survive.
PAIRS = [
    ("descriptions", "description", "descriptionType"),
    ("titles", "title", "titleType"),
    ("dates", "date", "dateType"),
    ("relatedIdentifiers", "relatedIdentifier", "relationType"),
    ("contributors", "name", "contributorType"),
    ("subjects", "subject", "subjectScheme"),
]


def leaves(value, key=None):
    if isinstance(value, dict):
        for k, v in value.items():
            if k not in SKIP_KEYS:
                yield from leaves(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from leaves(v, key)
    elif value not in (None, "") and not isinstance(value, bool):
        yield key, str(value)


def graph_strings(graph):
    found = set()
    for node in graph.all_nodes():
        found.add(str(node))
        if isinstance(node, rdflib.URIRef):
            found.add(str(node).rsplit("/", 1)[-1])
        elif isinstance(node, rdflib.Literal):
            found.add(str(node).strip())
    return found


def holder_values(graph, text):
    """Subjects whose text-carrying statement has this exact text."""
    return {s for s, p, o in graph if isinstance(o, rdflib.Literal) and str(o).strip() == text.strip()}


def pairs_recoverable(graph, attributes):
    ok = total = 0
    for list_key, text_key, qualifier_key in PAIRS:
        for item in attributes.get(list_key) or []:
            if not isinstance(item, dict) or not item.get(text_key) or not item.get(qualifier_key):
                continue
            total += 1
            wanted = str(item[qualifier_key])
            for holder in holder_values(graph, str(item[text_key])):
                qualifiers = {str(o).rsplit("/", 1)[-1] for p, o in graph.predicate_objects(holder)
                              if str(p).endswith("/" + qualifier_key)}
                if qualifiers == {wanted}:  # exactly one qualifier on the text's own node
                    ok += 1
                    break
    return ok, total


def measure(graph, attributes):
    record = rdflib.URIRef("https://doi.org/" + attributes["doi"])
    present = graph_strings(graph)
    values = list(leaves(attributes))
    lost = [(k, v) for k, v in values if ALIASES.get(v.strip(), v.strip()) not in present]
    ok, total = pairs_recoverable(graph, attributes)
    return {
        "triples": len(graph),
        "on_record": sum(1 for _ in graph.predicate_objects(record)),
        "nodes": len({s for s in graph.subjects() if isinstance(s, rdflib.BNode)}),
        "values": len(values),
        "lost": lost,
        "pairs": (ok, total),
        "invalid": sorted({str(p) for p in graph.predicates() if not str(p).startswith(("http://", "https://"))}),
    }


def main():
    before_ctx = load_context(HERE / "context-before.jsonld")
    after_ctx = load_context(ROOT / "production-namespace" / "context" / "fullcontext.jsonld")
    rows = []
    for name, path in RECORDS.items():
        attributes = record_attributes(path)
        results = {}
        for label, context, prepared in (("before", before_ctx, False), ("after", after_ctx, True),
                                         ("context-only", after_ctx, False)):
            graph = to_graph(attributes, context, prepared=prepared)
            if label != "context-only":
                (HERE / label).mkdir(exist_ok=True)
                # Canonical blank-node labels keep the files identical across runs.
                canonical = rdflib.Graph()  # rdflib 7 returns a read-only graph; copy it to bind prefixes
                canonical += to_canonical_graph(graph)
                for prefix, namespace in graph.namespaces():
                    canonical.bind(prefix, namespace, override=True)
                (HERE / label / f"{name}.ttl").write_text(canonical.serialize(format="turtle"), encoding="utf-8")
            results[label] = measure(graph, attributes)
        rows.append((name, attributes["doi"], results))

    out = ["# Results", "", "Generated by `compare.py`. Do not edit by hand.", "",
           "| Record | | Triples | Statements on the record | Structured nodes | JSON values lost | Text–type pairs readable | Invalid predicates |",
           "|---|---|---:|---:|---:|---:|---:|---|"]
    for name, doi, results in rows:
        for label in ("before", "after", "context-only"):
            r = results[label]
            ok, total = r["pairs"]
            out.append(f"| {name if label == 'before' else ''} | {label} | {r['triples']} | {r['on_record']} | {r['nodes']} | "
                       f"{len(r['lost'])} of {r['values']} | {ok} of {total} | {', '.join(r['invalid']) or 'none'} |")
    out += ["", "\"Context-only\" applies the new context to the unmodified record, without `prepare()`.", ""]
    for name, doi, results in rows:
        for label in ("before", "after"):
            lost = results[label]["lost"]
            if lost:
                keys = sorted({k for k, _ in lost})
                out.append(f"- **{name}, {label}:** values lost from keys {', '.join(f'`{k}`' for k in keys)}")
    (HERE / "RESULTS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
