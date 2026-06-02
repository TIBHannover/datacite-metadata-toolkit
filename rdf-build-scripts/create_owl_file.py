import json
from pathlib import Path
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, SKOS, DCTERMS

# this files folder
BASE_DIR = Path(__file__).resolve().parent

# folder that holds vocabs, classes and properties
SOURCE_DIR = BASE_DIR.parent / "rdf-vocabulary-staging"

def main():
    g = Graph()
    ontology_iri = URIRef("https://schema.stage.datacite.org/linked-data/")
    g.add((ontology_iri, RDF.type, OWL.Ontology))
    g.add((SKOS.ConceptScheme, RDF.type, OWL.Class))
    g.add((SKOS.Concept, RDF.type, OWL.Class))

    # Namespaces
    g.bind("rdfs", RDFS)
    g.bind("rdf", RDF)
    g.bind("schema", "https://schema.stage.datacite.org/linked-data/")
    g.bind("datacite", "https://schema.stage.datacite.org/linked-data/")
    g.bind("owl", OWL)
    g.bind("xsd", XSD)
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)


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
    g.serialize(destination=BASE_DIR / "datacite.owl", format="pretty-xml")

if __name__ == "__main__":
    main()