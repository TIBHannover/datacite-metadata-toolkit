"""Tests for validation-and-conversion/scripts/datacite_to_rdf.py and the JSON-LD context."""

import json
import sys
import unittest
from pathlib import Path

import pyshacl
import rdflib
from rdflib.compare import isomorphic

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "validation-and-conversion" / "scripts"))

from datacite_to_rdf import DEFAULT_CONTEXT, load_context, record_attributes, to_graph  # noqa: E402

EXAMPLES = ROOT / "validation-and-conversion" / "examples"
RECORDS = [EXAMPLES / "record.json", EXAMPLES / "real-dataset-dryad.json", EXAMPLES / "real-software-zenodo.json"]
SHAPES = ROOT / "validation-and-conversion" / "shapes" / "datacite-4.7-r2.shacl.ttl"
DIST = ROOT / "production-namespace" / "dist"
DCP = rdflib.Namespace("https://w3id.org/tib/datacite/property/")
DCC = rdflib.Namespace("https://w3id.org/tib/datacite/class/")
DCV = "https://w3id.org/tib/datacite/vocab/"
POSITION = rdflib.URIRef("https://schema.org/position")
# Derived citation formats and language codes (they become tags).
SKIP_KEYS = {"schemaOrg", "bibtex", "citeproc", "ris", "lang", "doi"}
# API list key -> DataCite property linking the owner to each item's node.
OWNED = {"titles": "title", "subjects": "subject", "dates": "date", "alternateIdentifiers": "alternateIdentifier",
         "identifiers": "alternateIdentifier", "relatedIdentifiers": "relatedIdentifier", "rightsList": "rights",
         "descriptions": "description", "creators": "creator", "contributors": "contributor",
         "fundingReferences": "fundingReference", "geoLocations": "geoLocation", "relatedItems": "relatedItem"}
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


def reachable_strings(graph, node, found=None):
    """Strings for every node reachable from node: literals, IRIs and IRI tails."""
    found = set() if found is None else found
    for o in graph.objects(node, None):
        text = str(o).strip()
        if text in found:
            continue
        found.add(text)
        if isinstance(o, rdflib.URIRef):
            found.add(text.rsplit("/", 1)[-1])
        else:
            reachable_strings(graph, o, found)
    return found


def misplaced(graph, owner, attributes, where=""):
    """Items whose values are not all found under one node linked from their owner."""
    problems = []
    for key, prop in OWNED.items():
        for index, item in enumerate(attributes.get(key) or []):
            if not isinstance(item, dict):
                continue
            values = {ALIASES.get(v, v) for _, v in leaves(item)}
            holders = [n for n in graph.objects(owner, DCP[prop]) if values <= reachable_strings(graph, n)]
            if not holders:
                problems.append(f"{where}{key}[{index}]")
            elif key == "relatedItems":
                problems += misplaced(graph, holders[0], item, f"{where}{key}[{index}].")
    return problems


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

    def test_each_item_stays_on_its_own_node(self):
        """Every value of a list item is found under one node linked from the item's owner."""
        for path in RECORDS:
            attributes, graph = convert(path)
            record = rdflib.URIRef("https://doi.org/" + attributes["doi"])
            self.assertEqual(misplaced(graph, record, attributes), [], path.name)

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

    def test_api_identifiers_become_alternate_identifiers(self):
        doi = "10.1234/test"
        attributes = {"doi": doi, "identifiers": [
            {"identifier": "ABC-123", "identifierType": "Local accession number"},
            {"identifier": "https://doi.org/" + doi, "identifierType": "DOI"}]}
        graph = to_graph(attributes, load_context(DEFAULT_CONTEXT))
        nodes = list(graph.objects(rdflib.URIRef("https://doi.org/" + doi), DCP.alternateIdentifier))
        self.assertEqual(len(nodes), 1, "the record's own DOI is not an alternate identifier")
        self.assertEqual(str(graph.value(nodes[0], rdflib.RDF.value)), "ABC-123")
        self.assertEqual(str(graph.value(nodes[0], DCP.alternateIdentifierType)), "Local accession number")

    def test_identifiers_repeating_alternate_identifiers_are_not_duplicated(self):
        self.assertEqual(len(list(self.graph.objects(self.record, DCP.alternateIdentifier))),
                         len(self.attributes["alternateIdentifiers"]))

    def test_related_item_publisher_is_a_node(self):
        item = next(self.graph.objects(self.record, DCP.relatedItem))
        publisher = next(self.graph.objects(item, DCP.publisher))
        self.assertIn((publisher, rdflib.RDF.type, DCC.Publisher), self.graph)
        self.assertEqual(str(next(self.graph.objects(publisher, rdflib.RDF.value))),
                         self.attributes["relatedItems"][0]["publisher"])


def creator_names(graph, subject):
    """Creator names sorted by schema:position."""
    nodes = sorted(graph.objects(subject, DCP.creator), key=lambda node: graph.value(node, POSITION).toPython())
    return [str(graph.value(node, DCP.creatorName)) for node in nodes]


class CreatorOrderTest(unittest.TestCase):
    def setUp(self):
        self.attributes = record_attributes(EXAMPLES / "real-dataset-dryad.json")
        self.record = rdflib.URIRef("https://doi.org/" + self.attributes["doi"])
        self.context = load_context(DEFAULT_CONTEXT)

    def test_positions_follow_priority_order(self):
        graph = to_graph(self.attributes, self.context)
        self.assertEqual(creator_names(graph, self.record), [c["name"] for c in self.attributes["creators"]])

    def test_reordering_creators_changes_the_graph(self):
        reordered = dict(self.attributes, creators=list(reversed(self.attributes["creators"])))
        self.assertFalse(isomorphic(to_graph(self.attributes, self.context), to_graph(reordered, self.context)))

    def test_related_item_creators_are_numbered(self):
        attributes = record_attributes(EXAMPLES / "record.json")
        graph = to_graph(attributes, self.context)
        item = next(graph.objects(rdflib.URIRef("https://doi.org/" + attributes["doi"]), DCP.relatedItem))
        self.assertEqual(creator_names(graph, item), [c["name"] for c in attributes["relatedItems"][0]["creators"]])


SHAPE_PREFIXES = """
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix dcp: <https://w3id.org/tib/datacite/property/> .
@prefix dcc: <https://w3id.org/tib/datacite/class/> .
@prefix dcv: <https://w3id.org/tib/datacite/vocab/> .
@prefix doi: <https://doi.org/> .
@prefix schema: <https://schema.org/> .
"""
# Each snippet breaks one rule of the rdf:value convention; the shapes must reject all of them.
BROKEN = {
    "publisher as plain text": 'doi:x dcp:publisher "Example Press" .',
    "identifier as a web address": 'doi:x dcp:alternateIdentifier [ a dcc:AlternateIdentifier ; '
                                   'rdf:value <https://example.org/1> ; dcp:alternateIdentifierType "URL" ] .',
    "creator without a name": 'doi:x dcp:creator [ a dcc:Creator ; schema:position 1 ] .',
    "creator without a position": 'doi:x dcp:creator [ a dcc:Creator ; dcp:creatorName "A" ] .',
    "two creators share a position": 'doi:x dcp:creator [ a dcc:Creator ; dcp:creatorName "A" ; schema:position 1 ] , '
                                     '[ a dcc:Creator ; dcp:creatorName "B" ; schema:position 1 ] .',
    "gap in creator positions": 'doi:x dcp:creator [ a dcc:Creator ; dcp:creatorName "A" ; schema:position 1 ] , '
                                '[ a dcc:Creator ; dcp:creatorName "B" ; schema:position 3 ] .',
    "creator position starts at 0": 'doi:x dcp:creator [ a dcc:Creator ; dcp:creatorName "A" ; schema:position 0 ] .',
    "language tag on a date": 'doi:x dcp:date [ a dcc:Date ; rdf:value "2020"@en ; '
                              'dcp:dateType <https://w3id.org/tib/datacite/vocab/dateType/Issued> ] .',
    "two texts on one title": 'doi:x dcp:title [ a dcc:Title ; rdf:value "One" , "Two" ] .',
    "title text missing": 'doi:x dcp:title [ a dcc:Title ] .',
    "undefined identifier type": 'doi:x dcp:identifier [ a dcc:Identifier ; rdf:value "x" ; '
                                 'dcp:identifierType <https://w3id.org/tib/datacite/vocab/identifierType/URL> ] .',
    "alternate identifier type as a term": 'doi:x dcp:alternateIdentifier [ a dcc:AlternateIdentifier ; rdf:value "1" ; '
                                           'dcp:alternateIdentifierType <https://w3id.org/tib/datacite/vocab/identifierType/DOI> ] .',
}


class ShapesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shapes = rdflib.Graph().parse(SHAPES)

    def conforms(self, graph):
        conforms, _, report = pyshacl.validate(graph, shacl_graph=self.shapes)
        return conforms, report

    def test_examples_conform(self):
        for path in RECORDS:
            _, graph = convert(path)
            conforms, report = self.conforms(graph)
            self.assertTrue(conforms, f"{path.name}:\n{report}")

    def test_shapes_reject_broken_structure(self):
        for name, snippet in BROKEN.items():
            with self.subTest(name):
                conforms, _ = self.conforms(rdflib.Graph().parse(data=SHAPE_PREFIXES + snippet, format="turtle"))
                self.assertFalse(conforms)


class VocabularyTest(unittest.TestCase):
    def test_rdf_value_is_not_declared_in_owl(self):
        """rdf:value is reserved in OWL 2 DL; the vocabulary only mentions it in scope notes."""
        for name in ["datacite-4.7-r2.owl", "datacite-4.7-r2-owl-properties.ttl", "datacite-4.7-r2.ttl"]:
            graph = rdflib.Graph().parse(DIST / name)
            uses = [t for t in graph if rdflib.RDF.value in t]
            self.assertEqual(uses, [], name)

    def test_emitted_controlled_values_are_defined(self):
        vocabulary = rdflib.Graph().parse(DIST / "datacite-4.7-r2.ttl")
        concepts = set(vocabulary.subjects(rdflib.RDF.type, rdflib.SKOS.Concept))
        for path in RECORDS:
            _, graph = convert(path)
            used = {o for o in graph.objects() if isinstance(o, rdflib.URIRef) and str(o).startswith(DCV)}
            self.assertEqual(sorted(used - concepts), [], path.name)


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
