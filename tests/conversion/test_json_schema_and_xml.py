"""Tests for the DataCite 4.7 JSON Schema, the 4.7 XSD and the XML-to-JSON converter."""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import jsonschema
import pyshacl
import rdflib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "validation-and-conversion" / "scripts"))

from convert import build_json_from_xml  # noqa: E402
from datacite_to_rdf import DEFAULT_CONTEXT, load_context, to_graph  # noqa: E402

EXAMPLES = ROOT / "validation-and-conversion" / "examples"
PROFILES = ROOT / "validation-and-conversion" / "schemas" / "schema-profiles"
SCHEMA = PROFILES / "datacite.schema.json"
XSD = ROOT / "validation-and-conversion" / "schemas" / "xsd"
CURRENT_VERSION = json.loads((ROOT / "rdf-vocabulary-staging" / "manifest" / "datacite-current.json").read_text(
    encoding="utf-8"))["currentVersion"]
SHAPES = ROOT / "validation-and-conversion" / "shapes" / f"datacite-{CURRENT_VERSION}.shacl.ttl"
DCP = rdflib.Namespace("https://w3id.org/tib/datacite/property/")
NS = "{http://datacite.org/schema/kernel-4}"
SQUARE = [{"polygonPoint": {"pointLatitude": lat, "pointLongitude": lon}} for lat, lon in [(0, 0), (0, 1), (1, 1), (0, 0)]]
EXAMPLE_RECORDS = ["record.json", "real-dataset-dryad.json", "real-software-zenodo.json", "datacite_example_filledin.json"]


def validator():
    return jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))


def attributes(name):
    data = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    return data.get("data", data).get("attributes", data)


def xml_47():
    """The full DataCite example with the 4.7 additions: relationTypeInformation and a Poster."""
    ET.register_namespace("", NS[1:-1])
    tree = ET.parse(EXAMPLES / "datacite-example-full-v4.xml")
    root = tree.getroot()
    root.find(f"{NS}relatedIdentifiers/{NS}relatedIdentifier").set("relationTypeInformation", "uses its sample data")
    root.find(f"{NS}relatedItems/{NS}relatedItem").set("relationTypeInformation", "chapter 2")
    root.find(f"{NS}resourceType").set("resourceTypeGeneral", "Poster")
    return ET.tostring(root, encoding="unicode")


class JsonSchemaTest(unittest.TestCase):
    def test_schema_is_valid_draft_2020_12(self):
        jsonschema.Draft202012Validator.check_schema(json.loads(SCHEMA.read_text(encoding="utf-8")))

    def test_controlled_lists_match_the_vocabularies(self):
        result = subprocess.run([sys.executable, str(ROOT / "rdf-build-scripts" / "build-json-schema.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_current_schema_is_the_current_versions_schema(self):
        """datacite.schema.json equals datacite-<current DataCite version>.schema.json apart from its $id,
        and the publication bundle carries both."""
        current = json.loads((ROOT / "rdf-vocabulary-staging" / "manifest" / "datacite-current.json").read_text(
            encoding="utf-8"))["currentVersion"].split("-r")[0]
        versioned = json.loads((PROFILES / f"datacite-{current}.schema.json").read_text(encoding="utf-8"))
        moving = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertTrue(versioned["$id"].endswith(f"/schema-profiles/datacite-{current}.schema.json"))
        self.assertTrue(moving["$id"].endswith("/schema-profiles/datacite.schema.json"))
        self.assertEqual(dict(versioned, **{"$id": None}), dict(moving, **{"$id": None}))
        for path in PROFILES.glob("datacite*.schema.json"):
            published = ROOT / "production-namespace" / "schema-profiles" / path.name
            self.assertEqual(published.read_text(encoding="utf-8"), path.read_text(encoding="utf-8"), path.name)

    def test_example_records_are_valid(self):
        for name in EXAMPLE_RECORDS:
            errors = [e.message for e in validator().iter_errors(json.loads((EXAMPLES / name).read_text(encoding="utf-8")))]
            self.assertEqual(errors, [], name)

    def test_attributes_alone_are_accepted(self):
        self.assertEqual(list(validator().iter_errors(attributes("real-software-zenodo.json"))), [])

    def test_api_spelling_of_crossref_funder_id_is_allowed(self):
        enum = json.loads(SCHEMA.read_text(encoding="utf-8"))["$defs"]["funderIdentifierType"]["enum"]
        self.assertIn("Crossref Funder ID", enum)
        self.assertNotIn("CrossrefFunderID", enum)

    def test_mistakes_are_reported(self):
        base = attributes("real-dataset-dryad.json")
        cases = {
            "misspelt resource type": lambda a: a["types"].update(resourceTypeGeneral="Datset"),
            "misspelt relation type": lambda a: a["relatedIdentifiers"].append(
                {"relatedIdentifier": "10.1/x", "relatedIdentifierType": "DOI", "relationType": "IsCitedby"}),
            "misspelt property name": lambda a: a.update(titel=[{"title": "x"}]),
            "no creators": lambda a: a.update(creators=[]),
            "contributor without a type": lambda a: a.update(contributors=[{"name": "A"}]),
            "empty name identifier": lambda a: a["creators"][0].update(
                nameIdentifiers=[{"nameIdentifier": None, "nameIdentifierScheme": "ORCID"}]),
            "related item without a title": lambda a: a.update(relatedItems=[{"relatedItemType": "Text",
                                                                              "relationType": "Cites"}]),
            "latitude out of range": lambda a: a.update(geoLocations=[{"geoLocationPoint": {
                "pointLatitude": 91, "pointLongitude": 0}}]),
            "publication year with a month": lambda a: a.update(publicationYear="2024-05"),
            "DOI written as a URL": lambda a: a.update(doi="https://doi.org/10.1234/x"),
            "funder identifier without its type": lambda a: a.update(fundingReferences=[
                {"funderName": "F", "funderIdentifier": "501100000780"}]),
            "latitude out of range, as text": lambda a: a.update(geoLocations=[{"geoLocationPoint": {
                "pointLatitude": "91", "pointLongitude": "0"}}]),
            "longitude out of range, as text": lambda a: a.update(geoLocations=[{"geoLocationPoint": {
                "pointLatitude": "0", "pointLongitude": "180.5"}}]),
            "polygon with one point, API form": lambda a: a.update(geoLocations=[{"geoLocationPolygon": [
                {"polygonPoint": {"pointLatitude": 1, "pointLongitude": 2}}]}]),
            "polygon with two inPolygonPoints": lambda a: a.update(geoLocations=[{"geoLocationPolygon": SQUARE + [
                {"inPolygonPoint": {"pointLatitude": 0.5, "pointLongitude": 0.5}}] * 2}]),
        }
        for name, change in cases.items():
            with self.subTest(name):
                record = copy.deepcopy(base)
                change(record)
                self.assertTrue(list(validator().iter_errors(record)), name)

    def test_valid_records_are_accepted(self):
        """Optional parts may be left out, and both number forms of a coordinate are checked alike."""
        base = attributes("real-dataset-dryad.json")
        cases = {
            "related item identifier without its type": lambda a: a.update(relatedItems=[{
                "relatedItemType": "Dataset", "relationType": "Cites", "titles": [{"title": "B"}],
                "relatedItemIdentifier": {"relatedItemIdentifier": "10.1234/B"}}]),
            "coordinates at the limits, as text": lambda a: a.update(geoLocations=[{"geoLocationPoint": {
                "pointLatitude": "-90.0", "pointLongitude": "180"}}]),
            "polygon with an inPolygonPoint": lambda a: a.update(geoLocations=[{"geoLocationPolygon": SQUARE + [
                {"inPolygonPoint": {"pointLatitude": 0.5, "pointLongitude": 0.5}}]}]),
            "two polygons": lambda a: a.update(geoLocations=[{"geoLocationPolygon": [SQUARE, SQUARE]}]),
            "funder identifier with its type": lambda a: a.update(fundingReferences=[
                {"funderName": "F", "funderIdentifier": "501100000780", "funderIdentifierType": "Crossref Funder ID"}]),
            "description without text": lambda a: a.update(descriptions=[{"descriptionType": "Abstract"}]),
        }
        for name, change in cases.items():
            with self.subTest(name):
                record = copy.deepcopy(base)
                change(record)
                self.assertEqual([e.message for e in validator().iter_errors(record)], [], name)
                conforms, _, report = pyshacl.validate(to_graph(record, load_context(DEFAULT_CONTEXT)),
                                                       shacl_graph=str(SHAPES))
                self.assertTrue(conforms, f"{name}:\n{report}")

    def test_47_additions_are_accepted(self):
        record = copy.deepcopy(attributes("real-dataset-dryad.json"))
        record["types"]["resourceTypeGeneral"] = "Presentation"
        record["relatedIdentifiers"] = [{"relatedIdentifier": "10.1/x", "relatedIdentifierType": "SWHID",
                                         "relationType": "Other", "relationTypeInformation": "was presented with"}]
        self.assertEqual([e.message for e in validator().iter_errors(record)], [])


def xml_rich():
    """A valid record whose names carry languages and whose geoLocation has two polygons, each with an inPolygonPoint."""
    ET.register_namespace("", NS[1:-1])
    root = ET.parse(EXAMPLES / "datacite-example-full-v4.xml").getroot()
    lang = "{http://www.w3.org/XML/1998/namespace}lang"
    root.find(f".//{NS}creatorName").set(lang, "fr")
    root.find(f".//{NS}contributorName").set(lang, "de")
    location = root.find(f"{NS}geoLocations/{NS}geoLocation")
    for polygon in location.findall(f"{NS}geoLocationPolygon"):
        location.remove(polygon)
    for offset in (0, 10):
        polygon = ET.SubElement(location, f"{NS}geoLocationPolygon")
        for tag, (lat, lon) in [("polygonPoint", p) for p in [(1, 1), (1, 2), (2, 2), (1, 1)]] + [("inPolygonPoint", (1.2, 1.5))]:
            point = ET.SubElement(polygon, f"{NS}{tag}")
            ET.SubElement(point, f"{NS}pointLatitude").text = str(lat + offset)
            ET.SubElement(point, f"{NS}pointLongitude").text = str(lon + offset)
    return ET.tostring(root, encoding="unicode")


class Xml47Test(unittest.TestCase):
    """A 4.7 XML record goes through every step: XSD, JSON, JSON Schema, RDF and SHACL."""

    def test_contributor_names_are_kept(self):
        record = build_json_from_xml((EXAMPLES / "datacite-example-full-v4.xml").read_text(encoding="utf-8"))
        contributors = record["data"]["attributes"]["contributors"]
        self.assertTrue(all(c["name"] for c in contributors))
        self.assertIn("Personal", {c["nameType"] for c in contributors})

    def test_relation_type_information_flows_through(self):
        record = build_json_from_xml(xml_47())
        attrs = record["data"]["attributes"]
        self.assertEqual(attrs["relatedIdentifiers"][0]["relationTypeInformation"], "uses its sample data")
        self.assertEqual(attrs["relatedItems"][0]["relationTypeInformation"], "chapter 2")
        self.assertEqual([e.message for e in validator().iter_errors(record)], [])
        graph = to_graph(attrs, load_context(DEFAULT_CONTEXT))
        self.assertEqual({str(o) for o in graph.objects(None, DCP.relationTypeInformation)},
                         {"uses its sample data", "chapter 2"})
        conforms, _, report = pyshacl.validate(graph, shacl_graph=str(SHAPES))
        self.assertTrue(conforms, report)

    def test_name_languages_polygons_and_inner_points_are_kept(self):
        attrs = build_json_from_xml(xml_rich())["data"]["attributes"]
        self.assertEqual((attrs["creators"][0]["lang"], attrs["contributors"][0]["lang"]), ("fr", "de"))
        polygons = attrs["geoLocations"][0]["geoLocationPolygon"]
        self.assertEqual(len(polygons), 2)
        for polygon in polygons:
            self.assertEqual([next(iter(entry)) for entry in polygon], ["polygonPoint"] * 4 + ["inPolygonPoint"])
        self.assertEqual([e.message for e in validator().iter_errors(attrs)], [])
        graph = to_graph(attrs, load_context(DEFAULT_CONTEXT))
        names = {(str(o), o.language) for o in graph.objects(None, DCP.creatorName)}
        self.assertIn(("ExampleFamilyName, ExampleGivenName", "fr"), names)
        self.assertIn("de", {o.language for o in graph.objects(None, DCP.contributorName)})
        nodes = list(graph.objects(None, DCP.geoLocationPolygon))
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            self.assertEqual(len(list(graph.objects(node, DCP.polygonPoint))), 4)
            self.assertIsNotNone(graph.value(node, DCP.inPolygonPoint))
        conforms, _, report = pyshacl.validate(graph, shacl_graph=str(SHAPES))
        self.assertTrue(conforms, report)

    @unittest.skipUnless(shutil.which("xmllint"), "xmllint is not installed")
    def test_rich_record_is_valid_xml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.xml"
            path.write_text(xml_rich(), encoding="utf-8")
            result = subprocess.run(["xmllint", "--noout", "--schema", str(XSD / "4.7" / "metadata.xsd"), str(path)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("xmllint"), "xmllint is not installed")
    def test_47_record_needs_the_47_xsd(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.xml"
            path.write_text(xml_47(), encoding="utf-8")

            def valid(version):
                return subprocess.run(["xmllint", "--noout", "--schema", str(XSD / version / "metadata.xsd"), str(path)],
                                      capture_output=True, text=True).returncode == 0

            self.assertTrue(valid("4.7"))
            self.assertFalse(valid("4.6"))


if __name__ == "__main__":
    unittest.main()
