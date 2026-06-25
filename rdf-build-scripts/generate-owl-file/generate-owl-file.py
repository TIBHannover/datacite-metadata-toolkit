import json
import os
from pathlib import Path
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD, SKOS, DCTERMS
from datetime import date

# this files folder
BASE_DIR = Path(__file__).resolve().parent
# folder that holds vocabs, classes and properties
SOURCE_DIR = BASE_DIR.parent.parent / "rdf-vocabulary-staging"

# env vars
NAMESPACE = os.environ.get("DATACITE_NAMESPACE", "https://w3id.org/tib/datacite/")
VERSION = os.environ.get("DATACITE_VERSION", "4.7")

def main():
    g = Graph()

    # namespaces
    g.bind("schema", NAMESPACE)
    g.bind("datacite", NAMESPACE)
    g.bind("rdfs", RDFS)
    g.bind("rdf", RDF)
    g.bind("xsd", XSD)
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)

    # metadata
    ontology_iri = URIRef(f"{NAMESPACE}dist/datacite")
    version_iri = URIRef(f"{NAMESPACE}dist/datacite-{VERSION}")
    manifest_iri = URIRef(f"{NAMESPACE}manifest/datacite-{VERSION}.json")

    g.add((ontology_iri, RDF.type, OWL.Ontology))
    g.add((ontology_iri, OWL.versionIRI, version_iri))
    g.add((ontology_iri, OWL.versionInfo, Literal(VERSION)))
    g.add((ontology_iri, DCTERMS.title,
           Literal(f"DataCite Linked Data Ontology {VERSION}", lang="en")))
    g.add((ontology_iri, DCTERMS.description, Literal(
        f"OWL representation of the DataCite linked-data vocabulary "
        f"for DataCite Metadata Schema {VERSION}.", lang="en")))
    g.add((ontology_iri, DCTERMS.created, Literal(date.today().isoformat(), datatype=XSD.date)))
    g.add((ontology_iri, DCTERMS.source, manifest_iri))
    g.add((ontology_iri, DCTERMS.license, URIRef("https://creativecommons.org/licenses/by/4.0/")))
    g.add((ontology_iri, DCTERMS.contributor, URIRef("https://github.com/selgebali")))
    g.add((ontology_iri, DCTERMS.contributor, URIRef("https://orcid.org/0000-0003-1378-5495")))
    g.add((ontology_iri, DCTERMS.contributor, URIRef("https://github.com/DenizJaeger")))

    # define ConceptScheme and Concept as classes
    g.add((SKOS.ConceptScheme, RDF.type, OWL.Class))
    g.add((SKOS.Concept, RDF.type, OWL.Class))

    # === vocabs ===
    counter = 0
    for folder in (SOURCE_DIR / "vocab").iterdir():
        if folder.is_dir():
            for file in folder.rglob("*.jsonld"):
                if file.name != "context.jsonld":
                    counter += 1
                    g.parse(file, format="json-ld")

                    # find subject iri
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # individual terms
                    if data.get("type") == "Concept":
                        vocab_iri = data.get("id")
                    # vocab schemes
                    elif data.get("@graph")[0].get("type") == "ConceptScheme":
                        vocab_iri = data.get("@graph")[0].get("id")
                    else:
                        raise Exception("Could not identify type and find Iri")

                    # add rdf:type owl:namedIndividual
                    g.add((URIRef(vocab_iri), RDF.type, OWL.NamedIndividual))

    print(f"{counter} jsonld files parsed from vocabulary directory")

    # === classes ===
    counter = 0
    for file in (SOURCE_DIR/"class").rglob("*.jsonld"):
        counter += 1
        g.parse(file, format="json-ld")
    print(f"{counter} jsonld files parsed from class directory")

    # === properties ===
    counter = 0
    for file in (SOURCE_DIR / "property").rglob("*.jsonld"):
        counter += 1
        g.parse(file, format="json-ld")
    print(f"{counter} jsonld files parsed from property directory")

    # write to RDF/XML file
    OUT_DIR = SOURCE_DIR / "dist"
    filename = f"datacite-{VERSION}.owl"
    g.serialize(destination=OUT_DIR/ filename, format="pretty-xml")

if __name__ == "__main__":
    main()
