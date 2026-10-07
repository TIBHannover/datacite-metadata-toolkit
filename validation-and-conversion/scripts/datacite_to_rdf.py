#!/usr/bin/env python3
"""Convert a DataCite REST API JSON record to RDF (Turtle) with the DataCite JSON-LD context.

Every repeatable DataCite element (description, title, date, ...) becomes its own
node, linked from the resource, with its text in rdf:value and its qualifiers
(type, scheme, language) beside it. Each creator records its place in DataCite's
priority order with schema:position (1 = first).

The JSON-LD context alone produces that structure. prepare() adds what a context
cannot: an explicit rdf:type on each node, the positions of creators and
polygon points, a language tag on the text (JSON-LD
cannot move a sibling "lang" key onto a value), a Publisher node for a publisher
given only as a name (as related items do), alternate identifiers that the REST
API lists under "identifiers", the bare DOI when the record writes it as a URL,
and coordinates and years given as JSON numbers written as text, so that the
context types them (xsd:float, xsd:gYear) the same way whichever form the record uses.

Identifier entries without a value (for example an ORCID scheme with
"nameIdentifier": null) are left out of the RDF, and a warning naming each
one is written to standard error; the rest of the record is still converted.

validation-and-conversion/shapes/datacite-4.7-r2.shacl.ttl checks the output.

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
# Identifiers that are left out when they have no value, with the keys that only qualify them.
IDENTIFIER_QUALIFIERS = {
    "affiliationIdentifier": ("affiliationIdentifierScheme", "schemeUri"),
    "publisherIdentifier": ("publisherIdentifierScheme", "schemeUri"),
    "funderIdentifier": ("funderIdentifierType", "schemeUri"),
}
# List key -> key holding the identifier that each entry exists to give.
IDENTIFIER_ENTRIES = {"nameIdentifiers": "nameIdentifier", "alternateIdentifiers": "alternateIdentifier",
                      "relatedIdentifiers": "relatedIdentifier"}
# Numbers the context types (xsd:float, xsd:gYear); JSON numbers become text so the digits are kept as written.
NUMBER_KEYS = {"pointLatitude", "pointLongitude", "westBoundLongitude", "eastBoundLongitude",
               "southBoundLatitude", "northBoundLatitude", "publicationYear"}
DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:")
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


def publisher_node(container):
    """Make the publisher a Publisher node, whether the record gives a bare name or an object."""
    publisher = container.get("publisher")
    if isinstance(publisher, str):
        publisher = container["publisher"] = {"name": publisher}
    if isinstance(publisher, dict):
        publisher["@type"] = "class:Publisher"
        tag_language(publisher, "name")


def as_list(value):
    return value if isinstance(value, list) else [] if value is None else [value]


def is_point_entry(entry):
    """One entry of an API polygon: {"polygonPoint": {...}} or {"inPolygonPoint": {...}}."""
    return isinstance(entry, dict) and (isinstance(entry.get("polygonPoint"), dict) or set(entry) == {"inPolygonPoint"})


def polygon_nodes(geo_location):
    """Give each polygon one node holding its points, numbered in drawing order, and its inPolygonPoint.

    The REST API lists one polygon as [{"polygonPoint": {...}}, ..., {"inPolygonPoint": {...}}]
    and several as a list of such lists; XML-shaped JSON uses {"polygonPoint": [...]}.
    """
    polygons = as_list(geo_location.get("geoLocationPolygon"))
    if polygons and all(is_point_entry(entry) for entry in polygons):
        polygons = [polygons]  # a single polygon, given as its list of points
    nodes = []
    for polygon in polygons:
        if isinstance(polygon, dict):
            polygon = [{"polygonPoint": point} for point in as_list(polygon.get("polygonPoint"))] + \
                      [{"inPolygonPoint": point} for point in as_list(polygon.get("inPolygonPoint"))]
        node = {"polygonPoint": []}
        for entry in as_list(polygon):
            if isinstance(entry, dict) and isinstance(entry.get("polygonPoint"), dict):
                node["polygonPoint"].append(dict(entry["polygonPoint"], position=len(node["polygonPoint"]) + 1))
            if isinstance(entry, dict) and isinstance(entry.get("inPolygonPoint"), dict):
                node["inPolygonPoint"] = entry["inPolygonPoint"]
        nodes.append(node)
    if nodes:
        geo_location["geoLocationPolygon"] = nodes


def type_items(container):
    """Add rdf:type and language tags to structured lists, including those nested in related items."""
    if isinstance(container.get("affiliation"), list):
        container["affiliation"] = [{"name": item} if isinstance(item, str) else item
                                    for item in container["affiliation"]]
    for key, (cls, text_key) in STRUCTURED.items():
        items = container.get(key)
        if not isinstance(items, list):
            continue
        for position, item in enumerate(items, start=1):
            if isinstance(item, dict):
                item["@type"] = cls
                if key == "creators":
                    item["position"] = position
                if key == "geoLocations":
                    polygon_nodes(item)
                tag_language(item, text_key)
                publisher_node(item)
                type_items(item)


def numbers_as_text(value):
    """Write coordinates and years given as JSON numbers as text, e.g. 2023 -> "2023"."""
    if isinstance(value, list):
        for item in value:
            numbers_as_text(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in NUMBER_KEYS and isinstance(item, (int, float)) and not isinstance(item, bool):
                value[key] = str(item)
            else:
                numbers_as_text(item)


def bare_doi(value):
    """10.1234/abc for "10.1234/abc", "https://doi.org/10.1234/abc" or "doi:10.1234/abc"."""
    value = str(value).strip()
    for prefix in DOI_PREFIXES:
        if value.lower().startswith(prefix):
            return value[len(prefix):]
    return value


def is_doi_of(entry, doi):
    value = bare_doi(entry.get("identifier", "")).lower()
    return str(entry.get("identifierType", "")).upper() == "DOI" and bool(doi) and value == bare_doi(doi).lower()


def merge_api_identifiers(record):
    """The REST API lists alternate identifiers under "identifiers" (the context ignores
    that key); add any not already in alternateIdentifiers, except the record's own DOI."""
    alternates = record.get("alternateIdentifiers") or []
    seen = {(a.get("alternateIdentifier"), a.get("alternateIdentifierType")) for a in alternates if isinstance(a, dict)}
    for entry in record.pop("identifiers", None) or []:
        if not isinstance(entry, dict) or is_blank(entry.get("identifier")) or is_doi_of(entry, record.get("doi")):
            continue
        key = (entry["identifier"], entry.get("identifierType"))
        if key not in seen:
            seen.add(key)
            alternate = {"alternateIdentifier": entry["identifier"]}
            if entry.get("identifierType"):
                alternate["alternateIdentifierType"] = entry["identifierType"]
            alternates.append(alternate)
    if alternates:
        record["alternateIdentifiers"] = alternates


def is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def drop_empty_identifiers(value, warnings, path="$"):
    """Leave out identifiers that have no value, and the entries that exist only to give one."""
    if isinstance(value, list):
        for index, item in enumerate(value):
            drop_empty_identifiers(item, warnings, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, qualifiers in IDENTIFIER_QUALIFIERS.items():
            if key in value and is_blank(value[key]):
                dropped = [key] + [q for q in qualifiers if q in value]
                for name in dropped:
                    del value[name]
                warnings.append(f"{path}: left out {', '.join(dropped)} because {key} has no value")
        item = value.get("relatedItemIdentifier")
        if isinstance(item, dict) and is_blank(item.get("relatedItemIdentifier")):
            del value["relatedItemIdentifier"]
            warnings.append(f"{path}: left out relatedItemIdentifier because it has no value")
        for key, item in list(value.items()):
            if key in IDENTIFIER_ENTRIES and isinstance(item, list):
                kept = []
                for index, entry in enumerate(item):
                    if isinstance(entry, dict) and is_blank(entry.get(IDENTIFIER_ENTRIES[key])):
                        warnings.append(f"{path}.{key}[{index}]: left out the entry because "
                                        f"{IDENTIFIER_ENTRIES[key]} has no value")
                    else:
                        kept.append(entry)
                value[key] = item = kept
            drop_empty_identifiers(item, warnings, f"{path}.{key}")


def prepare(attributes, warnings=None):
    """Return a copy of the record ready for the context; problems found are appended to warnings."""
    warnings = [] if warnings is None else warnings
    record = copy.deepcopy(attributes)
    if record.get("doi"):
        record["doi"] = bare_doi(record["doi"])
    drop_empty_identifiers(record, warnings)
    merge_api_identifiers(record)
    numbers_as_text(record)
    type_items(record)
    # The DOI is the record's identifier.
    if record.get("doi"):
        record["identifier"] = {"@type": "class:Identifier", "value": record["doi"], "identifierType": "DOI"}
    publisher_node(record)
    return record


def to_graph(attributes, context, prepared=True, warnings=None):
    record = prepare(attributes, warnings) if prepared else attributes
    document = {"@context": context, "@id": "https://doi.org/" + bare_doi(attributes["doi"]), **record}
    graph = rdflib.Graph()
    # Keep literals as the record writes them ("41.090", not "41.09").
    normalize, rdflib.NORMALIZE_LITERALS = rdflib.NORMALIZE_LITERALS, False
    try:
        graph.parse(data=json.dumps(document), format="json-ld")
    finally:
        rdflib.NORMALIZE_LITERALS = normalize
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
    warnings = []
    graph = to_graph(record_attributes(args.record), load_context(args.context), prepared=not args.no_prepare,
                     warnings=warnings)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    sys.stdout.write(graph.serialize(format="turtle"))


if __name__ == "__main__":
    main()
