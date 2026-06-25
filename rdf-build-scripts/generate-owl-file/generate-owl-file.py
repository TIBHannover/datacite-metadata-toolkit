import json
import os
from pathlib import Path
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD, SKOS, DCTERMS
from datetime import datetime
from xml.sax.saxutils import escape, quoteattr

# this files folder
BASE_DIR = Path(__file__).resolve().parent
# folder that holds vocabs, classes and properties
SOURCE_DIR = BASE_DIR.parent.parent / "rdf-vocabulary-staging"

# env vars
NAMESPACE = os.environ.get("DATACITE_NAMESPACE", "https://w3id.org/tib/datacite/")
VERSION = os.environ.get("DATACITE_VERSION", "4.7")

def validate_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError(f"Expected date in YYYY-MM-DD format, got {value!r}") from exc

def ontology_created_date():
    explicit = os.environ.get("DATACITE_CREATED_DATE")
    if explicit:
        return validate_date(explicit)

    manifest_path = SOURCE_DIR / "manifest" / f"datacite-{VERSION}.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    created = manifest.get("releaseDate") or manifest.get("created") or manifest.get("updated")
    if not created:
        raise ValueError(
            f"Could not find releaseDate, created, or updated in {manifest_path}"
        )
    return validate_date(created)

def term_key(term):
    return str(term)

def qname(g, uri):
    return g.namespace_manager.qname(uri)

def primary_type(types):
    ordered = [
        OWL.Ontology,
        RDFS.Class,
        RDF.Property,
        OWL.Class,
        SKOS.ConceptScheme,
        SKOS.Concept,
        OWL.NamedIndividual,
    ]
    for candidate in ordered:
        if candidate in types:
            return candidate
    return sorted(types, key=term_key)[0] if types else None

def write_deterministic_rdf_xml(g, destination):
    namespace_declarations = [
        ("rdf", RDF),
        ("rdfs", RDFS),
        ("owl", OWL),
        ("skos", SKOS),
        ("dcterms", DCTERMS),
        ("xsd", XSD),
    ]
    subjects = sorted(set(g.subjects()), key=term_key)

    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<rdf:RDF"]
    for prefix, namespace in namespace_declarations:
        lines.append(f"  xmlns:{prefix}={quoteattr(str(namespace))}")
    lines.append(">")

    for subject in subjects:
        subject_types = set(g.objects(subject, RDF.type))
        node_type = primary_type(subject_types)
        node_tag = qname(g, node_type) if node_type else "rdf:Description"
        lines.append(f"  <{node_tag} rdf:about={quoteattr(str(subject))}>")

        predicate_objects = []
        for predicate, obj in g.predicate_objects(subject):
            if predicate == RDF.type and obj == node_type:
                continue
            predicate_objects.append((predicate, obj))

        predicate_objects.sort(key=lambda item: (qname(g, item[0]), term_key(item[1])))

        for predicate, obj in predicate_objects:
            predicate_tag = qname(g, predicate)
            if isinstance(obj, URIRef):
                lines.append(f"    <{predicate_tag} rdf:resource={quoteattr(str(obj))}/>")
            elif isinstance(obj, Literal):
                attrs = []
                if obj.language:
                    attrs.append(f"xml:lang={quoteattr(obj.language)}")
                if obj.datatype:
                    attrs.append(f"rdf:datatype={quoteattr(str(obj.datatype))}")
                attr_text = f" {' '.join(attrs)}" if attrs else ""
                lines.append(f"    <{predicate_tag}{attr_text}>{escape(str(obj))}</{predicate_tag}>")
            else:
                raise TypeError(f"Unsupported RDF term in deterministic RDF/XML output: {obj!r}")

        lines.append(f"  </{node_tag}>")

    lines.append("</rdf:RDF>")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")

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
    g.add((ontology_iri, DCTERMS.created, Literal(ontology_created_date(), datatype=XSD.date)))
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

    # write to deterministic RDF/XML file
    OUT_DIR = SOURCE_DIR / "dist"
    filename = f"datacite-{VERSION}.owl"
    write_deterministic_rdf_xml(g, OUT_DIR / filename)

if __name__ == "__main__":
    main()
