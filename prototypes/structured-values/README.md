# Prototype: structured values for repeatable DataCite elements

> **Status: finished.** This prototype became revision 4.7-r2 of the namespace. The maintained converter is `validation-and-conversion/scripts/datacite_to_rdf.py`, the example records are in `validation-and-conversion/examples/`, and the SHACL shapes that check the output are in `validation-and-conversion/shapes/`. This folder is kept as the record of why the RDF shape changed, with before-and-after examples.

## The problem

In DataCite XML, one element carries text plus qualifiers:

```xml
<description descriptionType="Abstract" xml:lang="en">Example Abstract</description>
```

RDF can attach qualifiers only to a thing, not to a piece of text. The vocabulary used one property, `https://w3id.org/tib/datacite/property/description`, both for the link from a resource to a description and for the description text itself.

The published JSON-LD context made it worse. It used `@nest` for repeatable lists, which pours every item's fields straight onto the resource. With six descriptions you got six texts and six types on the resource, and no way to tell which type belonged to which text. It also dropped fields it had no terms for, such as creator names, ORCIDs and licence URLs.

**Before**: texts and types on the resource, unpaired.

```turtle
<https://doi.org/10.82433/B09Z-4K37>
    dcp:description "Example Abstract", "Example Methods", "Example Other" ;
    dcp:descriptionType descriptionType:Abstract, descriptionType:Methods, descriptionType:Other .
```

**After**: one node per description, with its text, language and type together.

```turtle
<https://doi.org/10.82433/B09Z-4K37>
    dcp:description [ a dcc:Description ;
            rdf:value "Example Methods"@en ;
            dcp:descriptionType descriptionType:Methods ],
        [ a dcc:Description ;
            rdf:value "Example Abstract"@en ;
            dcp:descriptionType descriptionType:Abstract ] .   # …and more
```

## What changed

- **Own nodes:** creators, contributors, titles, subjects, dates, identifiers, rights, descriptions, publishers, geolocations, funding references and related items each become a node, linked from the resource by the matching DataCite property, with the element's text in `rdf:value`.
- **Vocabulary:** fourteen properties gained an `rdfs:range` naming their class and a `skos:scopeNote` saying where the text goes. DataCite's definitions are unchanged.
- **Order:** creators and polygon points record their order with `schema:position`.
- **Crosswalks:** the mapping rows keep their meaning; `mappings/rdf-paths.json` gives the SPARQL path from which a converter reads each DataCite term in this RDF.

## Results

`compare.py` converts three records with the old context ("before") and the current converter ("after"), and writes `before/`, `after/` and [`RESULTS.md`](RESULTS.md). On 7 October 2026:

| Record | | JSON values lost | Text–type pairs readable |
|---|---|---:|---:|
| DataCite full example | before | 129 of 510 | 0 of 83 |
| | after | 0 of 510 | 83 of 83 |
| Dryad dataset ([10.5061/dryad.h44j0zq16](https://doi.org/10.5061/dryad.h44j0zq16)) | before | 33 of 102 | 5 of 17 |
| | after | 0 of 102 | 17 of 17 |
| Zenodo software ([10.5281/zenodo.22862110](https://doi.org/10.5281/zenodo.22862110)) | before | 8 of 59 | 1 of 9 |
| | after | 0 of 59 | 9 of 9 |

"Values lost" checks only that each JSON value appears somewhere in the RDF. Whether each value sits on the right node, with the right qualifier and in the right order, is checked by the regression tests in `tests/conversion/`.

## Files

| File | Purpose |
|---|---|
| `compare.py` | Regenerates `before/`, `after/` and `RESULTS.md` |
| `context-before.jsonld` | The context as published before this change |
| `to-schemaorg-dcterms.rq` | Example SPARQL query that reads the new structure and writes Schema.org and DCTERMS |

## Run it

```bash
pip install -r rdf-build-scripts/requirements-mappings.txt
python3 prototypes/structured-values/compare.py
```
