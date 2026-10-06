"""Tests for validation-and-conversion/scripts/datacite_to_rdf.py and the JSON-LD context."""

import json
import sys
import unittest
from pathlib import Path

import rdflib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "validation-and-conversion" / "scripts"))

from datacite_to_rdf import DEFAULT_CONTEXT, load_context, record_attributes, to_graph  # noqa: E402

EXAMPLES = ROOT / "validation-and-conversion" / "examples"
RECORDS = [EXAMPLES / "record.json", EXAMPLES / "real-dataset-dryad.json", EXAMPLES / "real-software-zenodo.json"]
DCP = rdflib.Namespace("https://w3id.org/tib/datacite/property/")
DCV = "https://w3id.org/tib/datacite/vocab/"
# Derived citation formats, language codes (they become tags) and the legacy
# "identifiers" list, which repeats alternateIdentifiers.
SKIP_KEYS = {"schemaOrg", "bibtex", "citeproc", "ris", "lang", "doi", "identifiers"}
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
        yield key, str(value).strip()


# JSON values the context deliberately translates to a vocabulary term.
ALIASES = {"Crossref Funder ID": "CrossrefFunderID"}
# Vocabulary property names whose DataCite API JSON key is spelled differently.
JSON_KEYS = {"rightsURI": "rightsUri", "schemeURI": "schemeUri", "valueURI": "valueUri", "awardURI": "awardUri",
             "creatorName": "name", "contributorName": "name", "identifier": "doi", "identifierType": "doi"}


def json_keys(value, found=None):
    found = set() if found is None else found
    if isinstance(value, dict):
        for k, v in value.items():
            found.add(k)
            json_keys(v, found)
    elif isinstance(value, list):
        for v in value:
            json_keys(v, found)
    return found


def graph_strings(graph):
    found = set()
    for node in graph.all_nodes():
        found.add(str(node).strip())
        if isinstance(node, rdflib.URIRef):
            found.add(str(node).rsplit("/", 1)[-1])
    return found


def convert(path):
    attributes = record_attributes(path)
    return attributes, to_graph(attributes, load_context(DEFAULT_CONTEXT))


class RecordConversionTest(unittest.TestCase):
    def test_no_values_lost(self):
        for path in RECORDS:
            attributes, graph = convert(path)
            present = graph_strings(graph)
            lost = [(k, v) for k, v in leaves(attributes) if ALIASES.get(v, v) not in present]
            self.assertEqual(lost, [], path.name)

    def test_each_text_keeps_its_own_type(self):
        for path in RECORDS:
            attributes, graph = convert(path)
            for list_key, text_key, qualifier_key in PAIRS:
                for item in attributes.get(list_key) or []:
                    if not (isinstance(item, dict) and item.get(text_key) and item.get(qualifier_key)):
                        continue
                    text = str(item[text_key]).strip()
                    holders = {s for s, _, o in graph if isinstance(o, rdflib.Literal) and str(o).strip() == text}
                    readable = any(
                        {str(o).rsplit("/", 1)[-1] for o in graph.objects(h, DCP[qualifier_key])} == {str(item[qualifier_key])}
                        for h in holders)
                    self.assertTrue(readable, f"{path.name}: {list_key} {text[:40]!r}")

    def test_only_absolute_predicates(self):
        for path in RECORDS:
            _, graph = convert(path)
            self.assertEqual({p for p in graph.predicates() if not str(p).startswith(("http://", "https://"))}, set())


class StructureTest(unittest.TestCase):
    def setUp(self):
        self.attributes, self.graph = convert(EXAMPLES / "record.json")
        self.record = rdflib.URIRef("https://doi.org/" + self.attributes["doi"])

    def test_descriptions_are_typed_nodes_with_tagged_text(self):
        nodes = list(self.graph.objects(self.record, DCP.description))
        self.assertEqual(len(nodes), len(self.attributes["descriptions"]))
        for node in nodes:
            self.assertIsInstance(node, rdflib.BNode)
            self.assertIn((node, rdflib.RDF.type, rdflib.URIRef("https://w3id.org/tib/datacite/class/Description")), self.graph)
            values = list(self.graph.objects(node, rdflib.RDF.value))
            self.assertEqual(len(values), 1)
            self.assertEqual(values[0].language, "en")
            self.assertEqual(len(list(self.graph.objects(node, DCP.descriptionType))), 1)

    def test_doi_is_the_identifier(self):
        node = next(self.graph.objects(self.record, DCP.identifier))
        self.assertEqual(str(next(self.graph.objects(node, rdflib.RDF.value))), self.attributes["doi"])
        self.assertEqual(str(next(self.graph.objects(node, DCP.identifierType))), DCV + "identifierType/DOI")

    def test_crossref_funder_id_maps_to_vocabulary_term(self):
        values = {str(o) for o in self.graph.objects(None, DCP.funderIdentifierType)}
        self.assertEqual(values, {DCV + "funderIdentifierType/CrossrefFunderID"})

    def test_identifier_that_is_not_a_web_address_is_kept(self):
        attributes = dict(self.attributes)
        attributes["creators"] = [{"name": "Example", "affiliation": [{"name": "Org", "affiliationIdentifier": "0000 0004 1936 7347"}]}]
        graph = to_graph(attributes, load_context(DEFAULT_CONTEXT))
        self.assertIn(rdflib.Literal("0000 0004 1936 7347"), set(graph.objects(None, DCP.affiliationIdentifier)))


class ContextTest(unittest.TestCase):
    def test_current_context_is_frozen_for_the_current_version(self):
        staging = ROOT / "rdf-vocabulary-staging"
        current = json.loads((staging / "manifest" / "datacite-current.json").read_text(encoding="utf-8"))["currentVersion"]
        frozen = staging / "context" / f"fullcontext-{current}.jsonld"
        self.assertEqual((staging / "context" / "fullcontext.jsonld").read_text(encoding="utf-8"),
                         frozen.read_text(encoding="utf-8"),
                         "Changing the context needs a new revision with its own frozen copy")

    def test_rdf_paths_find_the_example_values(self):
        doc = json.loads((ROOT / "mappings" / "rdf-paths.json").read_text(encoding="utf-8"))
        prefixes = "".join(f"PREFIX {k}: <{v}>\n" for k, v in doc["prefixes"].items())
        attributes, graph = convert(EXAMPLES / "record.json")
        record = rdflib.URIRef("https://doi.org/" + attributes["doi"])
        used = json_keys(attributes)
        empty = []
        for term, entry in doc["terms"].items():
            name = term.rsplit("/", 1)[-1]
            if "/property/" not in term or not entry.get("path") or JSON_KEYS.get(name, name) not in used:
                continue
            if not list(graph.query(prefixes + f"SELECT ?v WHERE {{ ?r {entry['path']} ?v }}", initBindings={"r": record})):
                empty.append(name)
        # The example's contributors have no name, so contributorName has no value to find.
        self.assertEqual(sorted(empty), ["contributorName"])


if __name__ == "__main__":
    unittest.main()
