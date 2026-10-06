#!/usr/bin/env python3
"""Convert a DataCite REST API JSON record to RDF (Turtle) with the DataCite JSON-LD context.

Every repeatable DataCite element (description, title, date, ...) becomes its own
node, linked from the resource, with its text in rdf:value and its qualifiers
(type, scheme, language) beside it.

The JSON-LD context alone produces that structure. prepare() adds what a context
cannot: an explicit rdf:type on each node, a language tag on the text (JSON-LD
cannot move a sibling "lang" key onto a value), and protection for identifiers
that are not web addresses, which a JSON-LD processor would otherwise drop.

Usage:
    python3 validation-and-conversion/scripts/datacite_to_rdf.py record.json > record.ttl
"""

import argparse
import copy
import json
import sys
from pathlib import Path

import rdflib

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTEXT = ROOT / "production-namespace" / "context" / "fullcontext.jsonld"

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
}
# Identifier fields the context reads as web addresses; other values stay text.
IDENTIFIER_KEYS = {"nameIdentifier", "affiliationIdentifier", "publisherIdentifier", "funderIdentifier"}
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


def protect_identifiers(value):
    """Keep identifiers such as "0000 0001 2096 9829" as text instead of letting them be dropped."""
    if isinstance(value, list):
        for item in value:
            protect_identifiers(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in IDENTIFIER_KEYS and isinstance(item, str) and not item.startswith(("http://", "https://", "urn:")):
                value[key] = {"@value": item}
            else:
                protect_identifiers(item)


def prepare(attributes):
    record = copy.deepcopy(attributes)
    protect_identifiers(record)
    type_items(record)
    # The DOI is the record's identifier; the API's legacy "identifiers" list
    # repeats alternateIdentifiers and is ignored by the context.
    if record.get("doi"):
        record["identifier"] = {"@type": "class:Identifier", "value": record["doi"], "identifierType": "DOI"}
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
    parser.add_argument("--context", default=str(DEFAULT_CONTEXT), help="JSON-LD context file")
    parser.add_argument("--no-prepare", action="store_true", help="use the JSON-LD context only")
    args = parser.parse_args()
    graph = to_graph(record_attributes(args.record), load_context(args.context), prepared=not args.no_prepare)
    sys.stdout.write(graph.serialize(format="turtle"))


if __name__ == "__main__":
    main()
