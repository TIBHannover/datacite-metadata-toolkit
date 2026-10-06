# Prototype: structured values for repeatable DataCite elements

This branch prototypes a fix for a reported ambiguity: `https://w3id.org/tib/datacite/property/description` was used both for the link from a resource to a description and for the description text itself. Testing showed the same flaw affects every repeatable DataCite element, and that the JSON-LD context lost data as a result.

## The problem

In DataCite XML, one element carries text plus qualifiers:

```xml
<description descriptionType="Abstract" xml:lang="en">Example Abstract</description>
```

RDF can only attach qualifiers to a thing, not to a piece of text. So each description needs its own node holding the text, its type and its language, and the resource needs a separate link to that node. The vocabulary had one property for both jobs.

The published JSON-LD context made it worse. It used `@nest` for repeatable lists, which pours every item's fields straight onto the resource. With six descriptions you get six texts and six types on the resource, and no way to tell which type belongs to which text. It also dropped fields it had no terms for, such as creator names, ORCIDs and licence URLs, and turned `lang` into an invalid statement.

## What this branch changes

**Context** (`rdf-vocabulary-staging/context/fullcontext.jsonld`, regenerated into `production-namespace/`)

- **Own nodes for each item:** creators, contributors, titles, subjects, dates, alternate and related identifiers, rights, descriptions, geolocations, funding references and related items. Each list item becomes its own node, linked from the resource by the matching DataCite property.
- **Text in `rdf:value`:** where the element's main text has no property of its own, it goes in `rdf:value` on the node. Creator and contributor names keep `creatorName` and `contributorName`.
- **Missing keys added:** `name`, `identifiers`, `nameIdentifiers`, `types`, `schemeUri`, `rightsUri`, `valueUri`, `awardUri`, `relatedMetadataScheme` and `schemeType`. These are the API spellings the converter emits.
- **Plain string lists:** `sizes` and `formats` link directly to `size` and `format`. `@nest` cannot hold plain strings.
- **`lang`:** maps to `dcterms:language` on the node instead of the invalid `@language` alias.

**Vocabulary** (14 property definitions in `rdf-vocabulary-staging/property/`, regenerated into `production-namespace/`, the OWL file and the per-term Turtle)

- **Range:** `creator`, `contributor`, `title`, `subject`, `date`, `alternateIdentifier`, `relatedIdentifier`, `rights`, `description`, `identifier`, `publisher`, `geoLocation`, `fundingReference` and `relatedItem` each gain an `rdfs:range` naming their class.
- **Scope note:** each also gains a `skos:scopeNote` explaining where the text and qualifiers go.
- **DataCite's definitions:** the definition text is unchanged.

**Prototype tools** (this folder)

| File | Purpose |
|---|---|
| `datacite_to_rdf.py` | Converts a DataCite API JSON record to Turtle with a given context. `prepare()` adds what a JSON-LD context cannot: an explicit class on each node and a language tag on the text. |
| `compare.py` | Converts every record in `records/` before and after, writes `before/`, `after/` and `RESULTS.md`. |
| `records/` | DataCite's full example record and two real records fetched from the DataCite API on 6 October 2026: a Dryad dataset ([10.5061/dryad.h44j0zq16](https://doi.org/10.5061/dryad.h44j0zq16)) and Zenodo software ([10.5281/zenodo.22862110](https://doi.org/10.5281/zenodo.22862110)). The base64 `xml` field was removed. |
| `context-before.jsonld` | The context as published before this change. |
| `to-schemaorg-dcterms.rq` | Example SPARQL query that reads the new structure and writes Schema.org and DCTERMS. |

## Before and after

DataCite's full example, descriptions only. **Before**: texts and types on the resource, unpaired.

```turtle
<https://doi.org/10.82433/B09Z-4K37>
    dcp:description "Example Abstract", "Example Methods", "Example Other",
        "Example SeriesInformation", "Example TableOfContents", "Example TechnicalInfo" ;
    dcp:descriptionType descriptionType:Abstract, descriptionType:Methods, descriptionType:Other,
        descriptionType:SeriesInformation, descriptionType:TableOfContents, descriptionType:TechnicalInfo .
```

**After**: one node per description, with its text, language and type together.

```turtle
<https://doi.org/10.82433/B09Z-4K37>
    dcp:description [ a dcc:Description ;
            rdf:value "Example Methods"@en ;
            dcp:descriptionType descriptionType:Methods ],
        [ a dcc:Description ;
            rdf:value "Example Abstract"@en ;
            dcp:descriptionType descriptionType:Abstract ] .   # …and four more
```

Creators in the real Dryad record, which previously lost their names and ORCIDs:

```turtle
dcp:creator [ a dcc:Creator ;
    dcp:creatorName "Ellingboe, Ethan" ;
    dcp:nameType nameType:Personal ;
    dcp:nameIdentifier [ rdf:value "https://orcid.org/0009-0007-5856-0886" ;
        dcp:nameIdentifierScheme "ORCID" ; dcp:schemeURI <https://orcid.org> ] ;
    dcp:affiliation [ rdf:value "University of Washington" ;
        dcp:affiliationIdentifier <https://ror.org/00cvxb145> ;
        dcp:affiliationIdentifierScheme "ROR" ; dcp:schemeURI <https://ror.org> ] ] .
```

## Results

From `RESULTS.md`:

| Record | | JSON values lost | Text–type pairs readable | Invalid statements |
|---|---|---:|---:|---|
| DataCite full example | before | 106 of 466 | 0 of 61 | `@language` |
| | after | 1 of 466 | 61 of 61 | none |
| Dryad dataset | before | 33 of 102 | 5 of 17 | none |
| | after | 0 of 102 | 17 of 17 | none |
| Zenodo software | before | 8 of 59 | 1 of 9 | `@language` |
| | after | 0 of 59 | 9 of 9 | none |

"Text–type pairs readable" counts descriptions, titles, dates, related identifiers, contributors and subjects whose text can be matched to exactly its own type or scheme. The context alone (without `prepare()`) gives the same values and pairs; `prepare()` only adds node classes and language tags.

The one remaining loss is a separate, older bug: DataCite writes `funderIdentifierType` as `Crossref Funder ID`, but the vocabulary term is `CrossrefFunderID`.

## How the mappings would change

The SSSOM files map DataCite *terms*. The structure change does not change what `description` or `title` mean ("the description of the resource", "the title of the resource"), so **all 32 affected SSSOM rows keep their triples**. What changes is how a converter reads the value from DataCite RDF, which matters wherever the target term holds plain text.

The 32 rows fall into two groups:

| | Target expects a thing (node) | Target expects text |
|---|---|---|
| Schema.org | `creator`, `contributor`, `publisher`, `funding`, `spatialCoverage`, `about` | `name` (title), `description`, `identifier` (×2), `keywords`, `conditionsOfAccess`, `license` (takes `rightsURI`) |
| DCTERMS | `creator`, `contributor`, `publisher`, `rights`, `spatial`, `subject` | `title`, `description`, `identifier` (×2), `date` |
| DCAT 3 | `creator`, `publisher`, `rights`, `spatial` | `title`, `description`, `identifier` (×2) |

**Example 1: target expects text.** `title → dcterms:title`. DCTERMS gives `dcterms:title` the range `rdfs:Literal`, so writing the DataCite link straight across would put a node where text is required.

```text
SSSOM row        datacite-prop:title  skos:closeMatch  dcterms:title        (unchanged)
comment before   Both name the resource; preserve language and title type independently.
comment after    Both name the resource. DataCite links to a Title node; take the text from
                 its rdf:value, which keeps the language tag. Only the title without a titleType
                 is the main title.
```

**Example 2: target expects text, chosen by type.** `descriptionType/Abstract → schema:abstract`. The rule needs the description node's type and its `rdf:value`, which are only connected after this change:

```sparql
?r dcp:description ?d .
?d dcp:descriptionType <https://w3id.org/tib/datacite/vocab/descriptionType/Abstract> ;
   rdf:value ?abstract .
# → ?r schema:abstract ?abstract
```

**Example 3: target expects a thing, which now fits.** `rights → dcterms:rights`. DCTERMS expects a `RightsStatement` node. The DataCite `Rights` node now holds the licence name, identifier and URI together, so the existing row `class:Rights closeMatch dcterms:RightsStatement` can be applied directly. Before, the licence URL was dropped entirely.

**Proposed edits to the mapping files**

1. **Comments:** update the comments of the 16 text-target rows to say where the value is (as in Example 1).
2. **Conversion rules:** add an optional `rdf_path` field to each conversion rule, next to the existing `source_path`. For example, `dcp:title/rdf:value` and `dcp:description/rdf:value [with dcp:descriptionType]`. `source_path` keeps describing the DataCite XML/JSON record, which this change does not touch.
3. **Checker:** teach `mapping_tools.py` to accept and check `rdf_path`.
4. **Unchanged:** link strengths, coverage outcomes, the Wikidata set and the JSKOS export for Cocoda.

`to-schemaorg-dcterms.rq` shows the conversion working: on the "before" files it produces nothing; on the "after" files it produces the abstract, main title and a `dcterms:RightsStatement` with the licence name and URL.

## Not done, and open questions

- **Breaking change:** anyone who already uses `dcp:description` (or `title`, `subject`, …) with plain text in RDF must move the text to the node's `rdf:value`. This needs a version bump and an announcement, including to the reporter.
- **`rdf:value` or a DataCite property:** `rdf:value` is the standard choice and the context already uses it for language and coordinates, but some communities prefer a named property per element.
- **What a context cannot do:** without `prepare()`, nodes are untyped (their class follows from the new `rdfs:range`) and the language is a `dcterms:language` statement rather than a tag on the text.
- **Whole-vocabulary downloads:** `dist/datacite-4.7.ttl`, `.rdf` and `.jsonld` were not rebuilt; that needs Apache Jena `riot`. The OWL file and per-term files are rebuilt.
- **Separate older bugs found while testing:**
  - `funderIdentifierType` value spelling, as above.
  - `nameIdentifier` and `affiliationIdentifier` are typed as web addresses, so a non-URL identifier becomes a broken relative address.

## Run it

```bash
pip install -r rdf-build-scripts/requirements-namespace.txt
cd prototypes/structured-values
python compare.py
python datacite_to_rdf.py records/real-dataset.json --context ../../production-namespace/context/fullcontext.jsonld
```
