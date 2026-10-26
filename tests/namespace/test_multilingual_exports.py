"""Check the actual published graphs preserve multilingual source annotations."""

import json
from pathlib import Path
import unittest

from rdflib import Graph, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, SKOS


ROOT = Path(__file__).resolve().parents[2]
STAGING = "https://schema.stage.datacite.org/linked-data/"
PRODUCTION = "https://w3id.org/tib/datacite/"
ANNOTATIONS = (SKOS.prefLabel, SKOS.definition, SKOS.changeNote, DCTERMS.modified)
FORMATS = {".jsonld": "json-ld", ".ttl": "turtle", ".rdf": "xml", ".owl": "xml"}


class MultilingualExportsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        staging = ROOT / "rdf-vocabulary-staging"
        cls.version = json.loads((staging / "manifest/datacite-current.json").read_text())["currentVersion"]
        cls.sources = []
        for path in sorted((staging / "vocab").rglob("*.jsonld")):
            if path.name == "context.jsonld":
                continue
            data = json.loads(path.read_text())
            labels = data.get("prefLabel")
            if not isinstance(labels, list) or not any(value.get("@language") == "cs" for value in labels):
                continue
            graph = Graph().parse(path, format="json-ld")
            subject = URIRef(data["id"])
            cls.sources.append((path.relative_to(staging), subject, {
                predicate: set(graph.objects(subject, predicate)) for predicate in ANNOTATIONS
            }))

    def assert_annotations(self, graph, subject, expected):
        for predicate, values in expected.items():
            self.assertTrue(values, f"Missing source annotation: {subject} {predicate}")
            self.assertEqual(set(graph.objects(subject, predicate)), values,
                             f"Export changed or dropped annotation: {subject} {predicate}")

    def test_combined_exports(self):
        self.assertTrue(self.sources, "No Czech source terms were checked")
        artifacts = [f"datacite-{self.version}{suffix}" for suffix in FORMATS]
        artifacts += [f"datacite{suffix}" for suffix in (".jsonld", ".ttl", ".rdf")]
        artifacts += [f"datacite-{self.version}-owl.jsonld", f"datacite-{self.version}-owl-properties.ttl"]
        for folder, namespace in (("rdf-vocabulary-staging", STAGING), ("production-namespace", PRODUCTION)):
            for name in artifacts:
                with self.subTest(folder=folder, artifact=name):
                    path = ROOT / folder / "dist" / name
                    graph = Graph().parse(path, format=FORMATS[path.suffix])
                    for _, source_subject, expected in self.sources:
                        subject = URIRef(str(source_subject).replace(STAGING, namespace, 1))
                        self.assert_annotations(graph, subject, expected)
                    if "-owl" in name:
                        self.assertIn((SKOS.changeNote, RDF.type, OWL.AnnotationProperty), graph)

    def test_production_term_exports(self):
        for relative_path, source_subject, expected in self.sources:
            subject = URIRef(str(source_subject).replace(STAGING, PRODUCTION, 1))
            for suffix in (".jsonld", ".ttl"):
                with self.subTest(term=str(relative_path), format=suffix):
                    path = (ROOT / "production-namespace" / relative_path).with_suffix(suffix)
                    graph = Graph().parse(path, format=FORMATS[suffix])
                    self.assert_annotations(graph, subject, expected)


if __name__ == "__main__":
    unittest.main()
