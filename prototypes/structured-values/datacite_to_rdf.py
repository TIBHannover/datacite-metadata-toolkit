#!/usr/bin/env python3
"""Convert a DataCite REST API JSON record to RDF (Turtle) with a JSON-LD context.

Prototype for the structured-values change: every repeatable DataCite element
(description, title, date, ...) becomes its own node, linked from the resource,
with its text in rdf:value and its qualifiers (type, scheme, language) beside it.

The JSON-LD context alone produces that structure. Two things a context cannot
do are added by prepare(): an explicit rdf:type on each node, and a language tag
on the text (JSON-LD cannot move a sibling "lang" key onto a value).
"""

import argparse
import copy
import json
import sys
from pathlib import Path

import rdflib

# List key -> (class of each item, key holding the item's text, if any).
STRUCTURED = {
    "creators": ("class:Creator", "name"),
    "contributors": ("class:Contributor", "name"),
    "titles": ("class:Title", "title"),
    "subjects": ("class:Subject", "subject"),
    "dates": ("class:Date", "date"),
    "alternateIdentifiers": ("class:AlternateIdentifier", "alternateIdentifier"),
    "relatedIdentifiers": ("class:RelatedIdentifier", "relatedIdentifier"),
    "rightsList": ("class:Rights", "rights"),
    "descriptions": ("class:Description", "description"),
    "geoLocations": ("class:GeoLocation", None),
    "fundingReferences": ("class:FundingReference", None),
    "relatedItems": ("class:RelatedItem", None),
    "identifiers": ("class:Identifier", "identifier"),
}
# REST API fields that are derived or transport-only, not DataCite metadata.
IGNORED = {"xml", "prefix", "suffix", "container", "url", "contentUrl", "state", "viewCount", "downloadCount",
           "citationCount", "partCount", "partOfCount", "referenceCount", "versionCount", "versionOfCount",
           "viewsOverTime", "downloadsOverTime", "citationsOverTime", "created", "registered", "published",
           "updated", "isActive", "reason", "landingPage", "metadataVersion", "schemaVersion", "source"}


def load_context(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["@context"]


def record_attributes(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    attributes = data.get("data", data).get("attributes", data)
    return {k: v for k, v in attributes.items() if k not in IGNORED}


def tag_language(item, text_key):
    """Turn {"description": "...", "lang": "en"} into a language-tagged value."""
    if text_key and isinstance(item.get(text_key), str) and item.get("lang"):
        item[text_key] = {"@value": item[text_key], "@language": item.pop("lang")}


def type_items(container):
    """Add rdf:type and language tags to structured lists, including those nested in related items."""
    for key, (cls, text_key) in STRUCTURED.items():
        items = container.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                item["@type"] = cls
                tag_language(item, text_key)
                type_items(item)


def prepare(attributes):
    record = copy.deepcopy(attributes)
    type_items(record)
    if isinstance(record.get("publisher"), dict):
        record["publisher"]["@type"] = "class:Publisher"
        tag_language(record["publisher"], "name")
    return record


def to_graph(attributes, context, prepared=True):
    record = prepare(attributes) if prepared else attributes
    document = {"@context": context, "@id": "https://doi.org/" + attributes["doi"], **record}
    graph = rdflib.Graph()
    graph.parse(data=json.dumps(document), format="json-ld")
    for prefix, namespace in {
        "dcp": "https://w3id.org/tib/datacite/property/",
        "dcc": "https://w3id.org/tib/datacite/class/",
        "dcv": "https://w3id.org/tib/datacite/vocab/",
        "doi": "https://doi.org/",
        "dcterms": "http://purl.org/dc/terms/",
    }.items():
        graph.bind(prefix, namespace)
    return graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", help="DataCite REST API JSON file")
    parser.add_argument("--context", default="production-namespace/context/fullcontext.jsonld")
    parser.add_argument("--no-prepare", action="store_true", help="use the JSON-LD context only")
    args = parser.parse_args()
    graph = to_graph(record_attributes(args.record), load_context(args.context), prepared=not args.no_prepare)
    sys.stdout.write(graph.serialize(format="turtle"))


if __name__ == "__main__":
    main()
