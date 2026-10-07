"""Regression tests for rdf-build-scripts/mapping_tools.py."""

import csv
import json
import re
import shutil
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rdf-build-scripts"))

from mapping_tools import (  # noqa: E402
    BASE, SCHEMA, SKOS, SUBJECT_SOURCE, MappingError, build, check_semantics, read_sssom, strict_tsv,
)


class StrictTsvTest(unittest.TestCase):
    def test_bare_quote_in_unquoted_cell_is_rejected(self):
        with self.assertRaises(MappingError):
            strict_tsv('a\troleName="DataCollector"\n', "test")

    def test_escaped_quotes_are_accepted(self):
        rows = strict_tsv('a\t"roleName=""DataCollector"""\n', "test")
        self.assertEqual(rows, [["a", 'roleName="DataCollector"']])


class SubjectSourceTest(unittest.TestCase):
    def test_every_set_names_the_datacite_47_schema(self):
        for path in sorted((ROOT / "mappings").glob("datacite-*.sssom.tsv")):
            metadata, _ = read_sssom(path)
            prefix, _, local = metadata["subject_source"].partition(":")
            self.assertEqual(metadata["curie_map"][prefix] + local, SUBJECT_SOURCE, path.name)

    def test_wrong_prefix_base_is_rejected(self):
        """The DCAT set once expanded to https://datacite-metadata-schema.readthedocs.iokernel-4.7/metadata.xsd."""
        source = ROOT / "mappings" / "datacite-dcat.sssom.tsv"
        text = source.read_text(encoding="utf-8").replace(
            "dataciteschema: https://schema.datacite.org/meta/", "dataciteschema: https://datacite-metadata-schema.readthedocs.io", 1)
        with tempfile.TemporaryDirectory() as directory:
            broken = Path(directory) / source.name
            broken.write_text(text, encoding="utf-8")
            with self.assertRaises(MappingError):
                read_sssom(broken)


class SemanticRegressionTest(unittest.TestCase):
    def assertRejected(self, subject, obj, predicate="relatedMatch"):
        with self.assertRaises(MappingError):
            check_semantics(BASE + subject, SKOS + predicate, obj, "test")

    def test_inverse_relations_cannot_reuse_forward_predicates(self):
        self.assertRejected("vocab/relationType/Reviews", SCHEMA + "reviews")
        self.assertRejected("vocab/relationType/IsCitedBy", SCHEMA + "citation")
        self.assertRejected("vocab/relationType/IsReferencedBy", SCHEMA + "citation")
        self.assertRejected("vocab/relationType/IsSourceOf", SCHEMA + "isBasedOn")

    def test_known_semantic_errors(self):
        self.assertRejected("vocab/relationType/IsRelatedTo", SCHEMA + "isRelatedTo")
        self.assertRejected("vocab/numberType/Article", SCHEMA + "issueNumber")
        self.assertRejected("vocab/resourceTypeGeneral/Model", SCHEMA + "3DModel", "exactMatch")

    def test_forward_relations_are_accepted(self):
        check_semantics(BASE + "vocab/relationType/Reviews", SKOS + "relatedMatch", SCHEMA + "itemReviewed", "test")
        check_semantics(BASE + "vocab/relationType/Cites", SKOS + "relatedMatch", SCHEMA + "citation", "test")


class RepositoryTest(unittest.TestCase):
    def test_repository_mappings_pass_check(self):
        counts, unique, sources = build(ROOT, check=True)
        self.assertEqual(set(counts), {"schemaorg", "dcterms", "dcat", "wikidata"})
        self.assertLessEqual(unique, sum(counts.values()))  # DCAT reuses DCTERMS triples
        self.assertGreater(sources, 0)

    def test_jskos_export_is_importable_by_cocoda(self):
        mappings = json.loads((ROOT / "mappings" / "jskos-mappings.json").read_text(encoding="utf-8"))
        self.assertIsInstance(mappings, list)  # jskos-server imports an array, not an envelope
        for mapping in mappings:
            self.assertEqual(mapping["fromScheme"]["uri"], "http://bartoc.org/en/node/21149")
            self.assertTrue(mapping["toScheme"]["uri"].startswith("http://bartoc.org/en/node/"))
            self.assertTrue(mapping["from"]["memberSet"][0]["prefLabel"]["en"])
            self.assertTrue(mapping["to"]["memberSet"][0]["prefLabel"]["en"])
            self.assertTrue(mapping["creator"][0]["uri"].startswith("https://orcid.org/"))

    def test_no_exact_matches_in_schemaorg_set(self):
        text = (ROOT / "mappings" / "datacite-schemaorg.sssom.tsv").read_text(encoding="utf-8")
        self.assertNotIn("skos:exactMatch", text)


class MutationTest(unittest.TestCase):
    """Copy the inputs to a temporary root and break one invariant at a time."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "mappings", self.root / "mappings")
        shutil.copytree(ROOT / "production-namespace", self.root / "production-namespace")
        shutil.copytree(ROOT / "website", self.root / "website")

    def tearDown(self):
        self.temp.cleanup()

    def edit(self, name, old, new):
        path = self.root / "mappings" / name
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_stale_export_fails_check(self):
        self.edit("SKOS_crosswalks.jsonld", "skos:relatedMatch", "skos:closeMatch")
        with self.assertRaisesRegex(MappingError, "Stale export"):
            build(self.root, check=True)

    def test_undefined_target_fails(self):
        self.edit("datacite-schemaorg.sssom.tsv", "schema:itemReviewed", "schema:itemReviewedd")
        with self.assertRaisesRegex(MappingError, "undefined target"):
            build(self.root, check=True)

    def test_unknown_source_fails(self):
        self.edit("datacite-dcterms.sssom.tsv", "datacite-prop:creator\t", "datacite-prop:creator/creatorName\t")
        with self.assertRaisesRegex(MappingError, "unknown canonical source"):
            build(self.root, check=True)

    def test_coverage_must_agree_with_sssom(self):
        path = self.root / "mappings" / "coverage" / "wikidata.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        record = next(r for r in document["records"] if r["status"] == "mapped")
        record["status"] = "no_equivalent"
        path.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(MappingError, "status and SSSOM mappings disagree"):
            build(self.root, check=True)

    def test_stale_published_copy_fails_check(self):
        path = self.root / "production-namespace" / "mappings" / "coverage" / "dcat.json"
        path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaisesRegex(MappingError, "Stale published mapping"):
            build(self.root, check=True)

    def test_stale_published_guide_fails_check(self):
        path = self.root / "website" / "crosswalk-guide.html"
        path.write_text(path.read_text(encoding="utf-8").replace("Crosswalk Guide", "Crosswalk Notes"), encoding="utf-8")
        with self.assertRaisesRegex(MappingError, "Stale published guide"):
            build(self.root, check=True)

    def test_build_regenerates_exports(self):
        (self.root / "mappings" / "jskos-mappings.json").write_text("{}", encoding="utf-8")
        build(self.root)
        build(self.root, check=True)


class GuideNumbersTest(unittest.TestCase):
    """The numbers in the crosswalk guide are typed by hand; they must match the mapping files."""

    TARGETS = {"Schema.org": "schemaorg", "Dublin Core": "dcterms", "DCAT": "dcat", "Wikidata": "wikidata"}
    PREDICATES = ["closeMatch", "broadMatch", "narrowMatch", "relatedMatch"]
    OUTCOMES = ["mapped", "conversion_only", "no_equivalent", "out_of_scope"]

    @staticmethod
    def bar(html, label, unit):
        """The flex values of the bar after "<label> <span>N <unit>", and N."""
        match = re.search(rf'bar-label">{re.escape(label)} <span>(\d+) {unit}', html)
        segment = html[match.end():html.index("</div></div>", match.end())]
        return int(match.group(1)), [int(v) for v in re.findall(r"flex:(\d+)", segment)]

    def test_guide_numbers_match_the_mapping_files(self):
        html = (ROOT / "website" / "crosswalk-guide.html").read_text(encoding="utf-8")
        total = 0
        for label, target in self.TARGETS.items():
            lines = [line for line in (ROOT / "mappings" / f"datacite-{target}.sssom.tsv").read_text(
                encoding="utf-8").splitlines() if line and not line.startswith("#")]
            rows = list(csv.DictReader(lines, delimiter="\t"))
            total += len(rows)
            predicates = Counter(row["predicate_id"].split(":", 1)[1] for row in rows)
            count, flex = self.bar(html, label, "rows")
            self.assertEqual(count, len(rows), label)
            self.assertEqual(flex, [predicates[p] for p in self.PREDICATES if predicates[p]], label)
            records = json.loads((ROOT / "mappings" / "coverage" / f"{target}.json").read_text(encoding="utf-8"))["records"]
            outcomes = Counter(record["status"] for record in records)
            count, flex = self.bar(html, label, "terms")
            self.assertEqual(count, len(records), label)
            self.assertEqual(flex, [outcomes[o] for o in self.OUTCOMES if outcomes[o]], label)
        self.assertIn(f'<div class="fact"><b>{total}</b><span>mapping rows</span></div>', html)


if __name__ == "__main__":
    unittest.main()
