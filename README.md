# DataCite Metadata Toolkit

Validate DataCite metadata, convert XML and JSON records to linked data, and understand how DataCite terms correspond to other vocabularies.

**DataCite schema: 4.7. RDF modelling revision: 4.7-r2.** The suffix `r2` names a revision of this toolkit's linked-data model; it is not a new DataCite schema release. Earlier 4.6 and 4.7 artifacts remain available for reference and compatibility.

This README is the main user guide, technical reference and contribution guide. You can use the toolkit without learning its build and release machinery.

## Find your starting point

| Your goal | Start here |
|---|---|
| I am new to DataCite or linked data | [What this toolkit does](#what-this-toolkit-does), then [Quick start](#quick-start) |
| I have my own JSON or XML record | [Work with your own records](#work-with-your-own-records) and [Validation rules and troubleshooting](#validation-rules-and-troubleshooting) |
| I need the RDF model or stable identifiers | [RDF model and JSON-LD context](#rdf-model-and-json-ld-context), [Namespace](#namespace-and-resolvable-iris) and [Versioning](#versioning-model) |
| I need a crosswalk to another vocabulary | [Crosswalk mappings](#crosswalk-mappings) |
| I want to contribute or report a problem | [Contribution guidelines](#contribution-guidelines) |
| I maintain or publish releases | [Build and publication](#build-and-publication), [New DataCite releases](#upgrading-to-a-new-datacite-version) and [Release acceptance checklist](#release-acceptance-checklist) |

Full contents: [Release status](#release-status) · [Repository layout](#repository-layout) · [Version history](#version-history) · [Glossary](#key-concepts) · [References](#references) · [License](#license)

## What this toolkit does

**Metadata** is a description of a research output: its title, creators, publisher, publication year, identifiers and other details. **DataCite** defines the fields and controlled values used in that description. A **DOI** identifies the output. **Linked data** gives fields and relationships shared web identifiers so other systems can interpret them.

| Deliverable | What you can do with it | Scope |
|---|---|---|
| RDF/JSON-LD vocabulary | Look up DataCite classes, properties and controlled values by permanent identifier | DataCite 4.7, with earlier distributions retained |
| JSON Schema and official XML XSDs | Check record structure, required fields and controlled values | JSON follows the documented rules below; XSD checks XML |
| XML-to-JSON converter | Produce a `data.attributes` document from a DataCite XML record | Validate the XML first; conversion itself is not validation |
| JSON-to-RDF converter | Produce DataCite RDF in Turtle from REST API JSON or its attributes | Use JSON validation before conversion and SHACL afterwards |
| SHACL shapes | Check the structure, datatypes, controlled terms and ordering of DataCite RDF | A structural RDF check, not a second full DataCite submission validator |
| Crosswalks and conversion recipes | Review correspondences with Schema.org, DCTERMS, DCAT 3 and Wikidata | Recipes describe conditional conversion; executable exporters to these targets are not provided |
| Build and publication scripts | Generate a reviewable public namespace bundle | Maintainer tools; publication is a separate PR-based step |

A successful validation means the record satisfies the rules of that validator. It does not establish that the metadata is true, that an identifier resolves, or that a target crosswalk is lossless. The DCAT mappings do not establish DCAT-AP conformance.

## Quick start

### 1. Get the repository and dependencies

Use **Node.js 20+** and Git. **Python 3.11+** is recommended (the CI baseline); Python 3.9 is also supported by the current tools. These instructions use a macOS/Linux shell; on Windows, use WSL for the same commands. A downloaded repository ZIP also works: extract it and open a terminal in its root instead of cloning.

```bash
git clone https://github.com/selgebali/datacite-metadata-toolkit.git
cd datacite-metadata-toolkit
python3 -m venv /tmp/datacite-toolkit-venv
source /tmp/datacite-toolkit-venv/bin/activate
python -m pip install -r rdf-build-scripts/requirements-mappings.txt
npm install
```

The temporary virtual environment keeps the Python packages separate from other projects. Activate it again in each new terminal; recreate it if your system cleans `/tmp`. All commands below run from the repository root. User workflows do not require Apache Jena or Ruby.

If you are testing changes from an unmerged PR, check out that PR's branch before following this walkthrough. A fresh clone of the default branch contains only changes already merged there. See [Release status](#release-status) for the distinction between repository changes and public files.

### 2. Validate a supplied JSON record

```bash
npm run --silent validate:json -- validation-and-conversion/examples/real-dataset-dryad.json
```

Expected result: a line ending in `real-dataset-dryad.json valid` and exit status **0**. A nonzero exit status means validation failed; inspect the reported field before converting.

### 3. Convert it to RDF and check the RDF

```bash
npm run --silent convert:rdf -- validation-and-conversion/examples/real-dataset-dryad.json > /tmp/datacite-record.ttl
python -m pyshacl -s validation-and-conversion/shapes/datacite-4.7-r2.shacl.ttl /tmp/datacite-record.ttl
```

Expected result: the report includes **`Conforms: True`**. The Turtle file is your converted record; open `/tmp/datacite-record.ttl` in a text editor. The file represents the same metadata as linked-data statements. Blank-node identifiers and statement order may differ between runs without changing the RDF meaning.

Warnings, if any, appear in the terminal rather than inside the Turtle file. Read them before using the output; conversion can succeed while leaving out an empty identifier or an unknown field.

### 4. Understand the result

A title is represented as a separate node linked to the DOI resource:

```turtle
@prefix dcp: <https://w3id.org/tib/datacite/property/> .
@prefix dcc: <https://w3id.org/tib/datacite/class/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<https://doi.org/10.1234/example> dcp:title [
    a dcc:Title ;
    rdf:value "An example dataset"@en
] .
```

Read it as: “this DOI resource has a title; that title's text is ‘An example dataset’, in English.” When several titles have different types or languages, each title keeps its own details.

### 5. Try your own minimal record

Save this as `/tmp/my-datacite-record.json`. The DOI is illustrative; these commands do not register it or send the record to DataCite.

```json
{
  "doi": "10.1234/example",
  "creators": [{ "name": "Doe, Jane", "nameType": "Personal" }],
  "titles": [{ "title": "An example dataset", "lang": "en" }],
  "publisher": { "name": "Example University" },
  "publicationYear": 2026,
  "types": { "resourceTypeGeneral": "Dataset" }
}
```

```bash
npm run --silent validate:json -- /tmp/my-datacite-record.json
npm run --silent convert:rdf -- /tmp/my-datacite-record.json > /tmp/my-datacite-record.ttl
python -m pyshacl -s validation-and-conversion/shapes/datacite-4.7-r2.shacl.ttl /tmp/my-datacite-record.ttl
```

Expect `valid` and `Conforms: True`. Continue with the next section when you need XML input, custom contexts or details of the validation rules.

## Release status

The current repository pointer names **4.7-r2**, which changes the structure of RDF records. Queries and converters written for the original 4.7 RDF may need updating. Use `context/fullcontext-4.7.jsonld` and `dist/datacite-4.7.*` when you need that earlier structure; unversioned context and distribution files follow the current revision.

**Publication baseline, checked 7 October 2026:** the public namespace points to 4.7-r2. The local correction work has been implemented; it must still complete review, integration and publication checks. Use the release checklist to record the evidence for each gate. Public contexts and shapes can therefore differ from this checkout until publication is completed. That difference is a release step, not evidence that the local fix failed.

The mappings, SHACL shapes and JSON Schema have GitHub Pages backend paths. Their canonical w3id routes depend on [perma-id/w3id.org#6828](https://github.com/perma-id/w3id.org/pull/6828). While that redirect change is pending, use the backend file URLs:

- [Crosswalk guide and mappings](https://tibhannover.github.io/datacite/mappings/)
- [4.7-r2 SHACL shapes](https://tibhannover.github.io/datacite/shapes/datacite-4.7-r2.shacl.ttl)
- [Current JSON Schema](https://tibhannover.github.io/datacite/schema-profiles/datacite.schema.json)

The local corrections include context syntax repairs, XML preservation, identifier and polygon validation fixes, warnings for unknown JSON keys, and frozen-release protection. Completion is established by the [release checklist](#release-acceptance-checklist), not by this list of planned changes. Local quick-start commands use local artifacts; download public files only when you intend to use the published state.

## Work with your own records

### Validate JSON

`validation-and-conversion/schemas/schema-profiles/datacite.schema.json` checks a DataCite record in REST API JSON against DataCite 4.7: required properties, allowed controlled values, and the shape of each property. It accepts a full `{"data": {"attributes": …}}` document or the `attributes` object alone, and reports unknown keys, so a misspelt property name is caught.

```bash
npm install
npm run --silent validate:json -- your-record.json
```

Or in Python (`pip install jsonschema`):

```python
import json, jsonschema
schema = json.load(open("validation-and-conversion/schemas/schema-profiles/datacite.schema.json"))
record = json.load(open("your-record.json"))
for error in jsonschema.Draft202012Validator(schema).iter_errors(record):
    print("/".join(map(str, error.absolute_path)), error.message)
```

See [Validation rules and troubleshooting](#validation-rules-and-troubleshooting) for the rules and limitations.

The Python example lists errors; it does not set a failing process exit status. For shell automation, use the npm validation command or handle errors explicitly in your Python program.

### Validate and convert XML

`validation-and-conversion/scripts/validate_xml.rb` validates an XML file against DataCite's official 4.7 XSD (`schemas/xsd/4.7/`). Pass `--xsd validation-and-conversion/schemas/xsd/4.6/metadata.xsd` to check against 4.6 instead. Requires Ruby and the `nokogiri` gem (`gem install nokogiri`).

```bash
ruby validation-and-conversion/scripts/validate_xml.rb validation-and-conversion/examples/datacite-example-full-v4.xml
```

Without Ruby, `xmllint` gives the same result: `xmllint --noout --schema validation-and-conversion/schemas/xsd/4.7/metadata.xsd record.xml`.

`validation-and-conversion/scripts/convert.py` parses a DataCite XML file and produces a JSON payload matching the DataCite REST API structure (a `data.attributes` envelope), including the 4.7 `relationTypeInformation`. Python 3 only — no external packages required.

```bash
python3 validation-and-conversion/scripts/convert.py \
    validation-and-conversion/examples/datacite-example-full-v4.xml \
    --output /tmp/datacite-from-xml.json
```

Continue through JSON validation, conversion and SHACL:

```bash
npm run --silent validate:json -- /tmp/datacite-from-xml.json
npm run --silent convert:rdf -- /tmp/datacite-from-xml.json > /tmp/datacite-from-xml.ttl
python -m pyshacl -s validation-and-conversion/shapes/datacite-4.7-r2.shacl.ttl /tmp/datacite-from-xml.ttl
```

The XML converter preserves the original XML as a base64 `xml` field and adds derived API-style fields. Retaining that original is useful for provenance; it does not replace checks that the structured metadata survived conversion. An XSD-valid XML record may still fail a documented JSON rule; see the related-item title policy below.

### Convert JSON to DataCite RDF

```bash
npm run --silent validate:json -- /tmp/my-datacite-record.json
npm run --silent convert:rdf -- /tmp/my-datacite-record.json > /tmp/my-datacite-record.ttl
python -m pyshacl -s validation-and-conversion/shapes/datacite-4.7-r2.shacl.ttl /tmp/my-datacite-record.ttl
```

Use `--context` to select a local JSON-LD context explicitly:

```bash
npm run --silent convert:rdf -- /tmp/my-datacite-record.json \
  --context rdf-vocabulary-staging/context/fullcontext-4.7-r2.jsonld > /tmp/my-datacite-record.ttl
```

The maintained converter prepares records for the r2 model. Selecting the old 4.7 context does not make that preparation a backward-compatible old-model exporter. Its `--no-prepare` option is for inspecting context-only behaviour; it omits node typing, language tagging and ordering preparation and is not the normal validated conversion path.

### Browse the vocabulary

Start with `rdf-vocabulary-staging/manifest/datacite-current.json` to see the current revision, then open `rdf-vocabulary-staging/manifest/datacite-4.7-r2.json` for its index of classes, properties, and vocabulary terms. Earlier versioned manifests describe the earlier snapshots.

Individual term files follow a predictable structure:

- **Class files** (`class/Resource.jsonld`) — define the IRI, `rdf:type`, `rdfs:label`, and `rdfs:comment` for a DataCite entity.
- **Property files** (`property/identifier.jsonld`) — define the IRI and (where applicable) domain/range for a DataCite metadata field.
- **Vocab term files** (`vocab/resourceTypeGeneral/Dataset.jsonld`) — define a controlled term with `skos:prefLabel`, `skos:definition`, `skos:inScheme`, and optional `skos:closeMatch` mappings.

For the human-facing pages, start at the [namespace website](https://tibhannover.github.io/datacite/) or open `website/docs-index.html` locally. Individual identifiers and publication files are described in [Namespace](#namespace-and-resolvable-iris).

---

## Validation rules and troubleshooting

### Choose the right validator

| Layer | Checks | Does not establish |
|---|---|---|
| XML XSD | XML structure, required attributes, controlled lists and XSD datatypes | Every rule stated in the prose documentation, JSON/RDF correctness or identifier resolution |
| JSON Schema | API JSON structure, required metadata, controlled lists and unknown keys | All semantic conditions, geometric validity or RDF structure |
| SHACL | Structured RDF nodes, value datatypes, coordinate bounds, controlled terms and creator/polygon positions | All DataCite required fields, source fields discarded before RDF generation or factual accuracy |
| Mapping validators | Source/target existence in the pinned inventories, interchange syntax, coverage accounting and export agreement | Independent approval of every mapping's meaning or executable target export conformance |

Use **XML validation → JSON validation → RDF conversion → SHACL** for XML input, and **JSON validation → RDF conversion → SHACL** for JSON input. Stop at a failed check. Conversion warnings require review even when the process exits successfully.

### JSON Schema files and general rules

The JSON Schema (draft 2020-12) describes DataCite DOI records as the REST API returns and accepts them. It comes in two forms, like the vocabulary downloads:

| File | Changes over time? | Use it when you want… |
|---|---|---|
| `datacite-4.7.schema.json` (one per DataCite version) | No, once its version is no longer current | The rules of one DataCite release |
| `datacite.schema.json` | Yes, follows the current version's rules (with its own `$id`) | The newest rules, from one stable address |

Once published, both resolve at their `$id`, for example `https://w3id.org/tib/datacite/schema-profiles/datacite.schema.json` (the w3id address works after perma-id/w3id.org#6828 is merged; the files are served from `https://tibhannover.github.io/datacite/schema-profiles/`).

- **Required:** `doi`, at least one creator with a name, at least one title, `publisher`, `publicationYear` and `types.resourceTypeGeneral`, as DataCite requires for a registered DOI.
- **Controlled values:** every controlled list (`resourceTypeGeneral`, `relationType`, `contributorType`, ...) is generated from the vocabulary files by `python3 rdf-build-scripts/build-json-schema.py`, using the spelling the REST API uses (for example `Crossref Funder ID`). When a DataCite release adds terms, the release tooling adds the vocabulary files and this script carries them into the schema; `npm run check:json-schema` fails if they disagree.
- **4.7 additions:** `Poster` and `Presentation`, `RAiD` and `SWHID`, relation type `Other`, and `relationTypeInformation` on related identifiers and related items.
- **REST API fields** that are not DataCite metadata (`url`, `state`, `viewCount`, `created`, ...) are accepted without checks. Null values are accepted for optional fields, as the REST API returns them.

The optional live-sample tool runs the JSON Schema, converter and SHACL checks against randomly selected public API records. Save the input sample and capture the summary when citing a result:

```bash
npm run --silent check:live-sample -- --size 300 --save /tmp/datacite-sample.json > /tmp/datacite-sample-results.txt
```

The command requires network access and can take several minutes. It fetches metadata and does not modify DataCite records. It is an exploratory diagnostic: its success exit status does not mean every sampled record validated. Random samples and mutable API records make runs differ. Archive the sample, output, repository commit, dependency versions, run date and manual classifications before making a numerical accuracy claim. A sample cannot prove there are no false alarms.

**Dated exploratory result, 7 October 2026:** the maintainer recorded 18 flagged records in a 300-record run and reviewed the reported problems against the XSD and documentation. That result describes one reviewed sample, not a general error rate; the exact input/output must be archived to reproduce the numerical result.

**Rules stricter than the DataCite XSD.** The schema rejects empty titles, creator names, subjects, dates and identifiers, which the XSD accepts but which carry no information. It also requires related-item titles, which the DataCite documentation makes mandatory but the XSD does not enforce. Each such field says so in its description in the schema.

The schema checks structure and values, not meaning: it does not check that a date is a real date or that an identifier resolves. For linked data, use the JSON-LD context and the converter described above.

The earlier 4.6 profiles are kept, unmaintained, in `schema-profiles/legacy-4.6/`.

### Related items, identifiers and polygons

- **Related-item titles stay required.** [DataCite 4.7 property 20.3](https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/relateditem/#title) specifies one or more titles. The XSD leaves the titles element optional. The JSON Schema follows the prose documentation, so an XML record without that title can pass the XSD and fail JSON validation. This difference is deliberate and stated in the schema.
- **Related-item identifier type is optional.** [Property 20.1.a](https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/relateditem/#relateditemidentifiertype) and the XSD both allow its omission. Do not confuse it with a relatedIdentifier, whose identifier type and relation type are required.
- **A supplied funder identifier needs its type.** The JSON rule follows the XSD's required funderIdentifierType attribute. Leave out an absent identifier rather than providing a type alone.
- **Descriptions may omit text.** A description with a valid descriptionType and no text is accepted by the XSD, JSON Schema and shapes. It remains a typed node; no text is invented. This differs from the deliberate nonempty-value policies for titles, names, subjects, dates and identifiers.
- **A polygon needs at least four drawing points.** API list representations and object representations should enforce the same minimum. An optional inPolygonPoint is separate from the boundary points. DataCite also requires a closed boundary; the toolkit's minimum-count and order checks are not a full geometric validity test.
- **Coordinates receive bounds checks in both forms.** The current schema accepts JSON numbers and numeric text and checks latitude −90 to 90 and longitude −180 to 180. Numbers use numeric constraints; accepted text uses bounded patterns. Both `91` and `"91"` are rejected as latitudes. Conversion types coordinates as `xsd:float`, and SHACL also checks the bounds. Run SHACL for either representation.

These rules are implemented in the current correction checkout. The release checklist still requires passing checks and publication verification before announcing the corrected public release.

### Warnings and discarded fields

The RDF converter writes warnings to **standard error** and Turtle to **standard output**. It leaves out empty identifier entries with their qualifiers and names the location, such as `$.creators[0].nameIdentifiers[0]`. Unknown keys such as `titel` also produce a warning because the context cannot represent them. The JSON validator rejects unknown metadata keys earlier.

Derived and transport-only API fields such as `xml`, `url`, usage counts and timestamps are deliberately omitted from DataCite RDF. Accepted API fields are not all metadata fields, and acceptance by JSON Schema does not mean each has an RDF mapping. Preserve the source record when you need that information. Warnings are a diagnostic aid; they do not replace JSON validation.

### Fix a failed check

| Symptom | What to do |
|---|---|
| `node`, `npm` or `python3` is not found | Install the prerequisites, then reopen the terminal. Check `node --version` and `python3 --version`. |
| `ModuleNotFoundError` for rdflib, pyshacl or jsonschema | Activate the virtual environment and rerun its `python -m pip install -r ...` command from the quick start. |
| pip reports an externally managed environment | Use the virtual environment in the quick start instead of changing system Python. |
| JSON reports an unknown property such as `titel` | Correct the spelling to `titles`, with a list of title objects; run validation again. |
| A required field is missing | Add the actual metadata at the reported path. For example, `contributors/0` means the first contributor (array indexes start at 0); supply its real contributorType. Required root fields include creators, titles, publisher, year, DOI and general resource type. |
| A controlled value is rejected | Use the exact spelling and capitalization in the schema, for example `Dataset` and `IsCitedBy`. |
| A validator reports an out-of-range coordinate | Correct the latitude/longitude. Both JSON numbers and accepted numeric text are checked; rerun JSON validation and SHACL. |
| A related item passes XML but fails JSON for missing titles | Add its title. The JSON rule follows the documented 1–n requirement. |
| Conversion warns that an identifier has no value | Supply the real identifier or remove the incomplete entry; do not invent a value to silence the warning. |
| Conversion warns that a key is not defined | Correct a typo, or retain an intentional extension in the source record and document its separate handling. |
| SHACL says `Conforms: False` | Read its focus node, result path and message; correct the source JSON and regenerate RDF. |
| A w3id download returns 404 | Check the dated release status and use the GitHub Pages backend URL for the same file while redirects are pending. |

For example, this fragment is invalid:

```json
{ "titel": [{ "title": "A dataset" }] }
```

The corrected fragment is:

```json
{ "titles": [{ "title": "A dataset" }] }
```

These are fragments to repair inside a complete record, not complete DOI records on their own. If you report a bug, include the smallest failing record and the exact command/output; see [Contribution guidelines](#contribution-guidelines).

---

## RDF model and JSON-LD context

`rdf-vocabulary-staging/context/fullcontext.jsonld` maps the keys of DataCite REST API JSON to their full IRIs. Reference it in your JSON-LD documents:

```json
{
  "@context": "https://w3id.org/tib/datacite/context/fullcontext.jsonld",
  "@id": "https://doi.org/10.1234/example",
  "titles": [{ "title": "Example title", "titleType": "Subtitle" }],
  "creators": [{ "name": "Smith, Jane", "nameType": "Personal" }]
}
```

Each title and creator becomes its own node: the title text is in `rdf:value` beside its `titleType`, and the name is in `creatorName`. This fragment demonstrates the context, not a complete valid DataCite record. A context alone cannot add node types, language tags or creator positions; use the converter for the complete r2 preparation:

```bash
npm run --silent convert:rdf -- validation-and-conversion/examples/real-dataset-dryad.json > record.ttl
python3 -m pyshacl -s validation-and-conversion/shapes/datacite-4.7-r2.shacl.ttl record.ttl
```

`pip install -r rdf-build-scripts/requirements-mappings.txt` installs the Python dependencies of both commands. (`python3 -m pyshacl` works even when pip's script folder is not on your `PATH`.)

The converter reads a DataCite REST API record, or a bare `attributes` object, and writes Turtle:

- **DOI:** the record's IRI is `https://doi.org/<doi>`. A DOI written as `https://doi.org/…` or `doi:…` is reduced to the bare DOI first.
- **Unknown keys:** a key the context does not define, such as a misspelt `titel`, is left out with a warning. Check the record with the JSON Schema first to catch these.
- **Empty identifiers:** an identifier entry without a value, such as an ORCID scheme with `"nameIdentifier": null` or an empty `affiliationIdentifier`, is left out together with its scheme. The converter prints a warning naming each one (for example `warning: $.creators[0].nameIdentifiers[0]: left out the entry because nameIdentifier has no value`) and converts the rest of the record.
- **Value types:** identifier values (`nameIdentifier`, `affiliationIdentifier`, `publisherIdentifier`, `funderIdentifier`, ...) are always text, even when they look like web addresses, because many schemes are not web addresses. Fields that DataCite defines as URIs (`schemeUri`, `rightsUri`, `valueUri`, `awardUri`) are links. Coordinates are `xsd:float` numbers and `publicationYear` is an `xsd:gYear`, whether the record writes them as JSON numbers or as text.

The SHACL shapes check these conventions: at most one text in `rdf:value`, required for elements such as titles but optional for rights and descriptions; identifiers as text; coordinates and years with their datatypes; creators and polygon points numbered with `schema:position`; and every controlled value a real term of its DataCite vocabulary, so a misspelling such as `IsCitedby` is reported. The controlled-value part of the shapes is generated from the vocabularies by `python3 rdf-build-scripts/build-shapes.py`.

### Reading and querying the graph

Most repeatable text elements use a linked node with the text in `rdf:value`. Creator and contributor names use `dcp:creatorName` and `dcp:contributorName`. Qualifiers belong to that same element's node. Publisher names use `rdf:value`, including publishers in related items. The resource type fields sit on the described resource.

This SPARQL query retrieves titles and their optional types/languages from a converted graph:

```sparql
PREFIX dcp: <https://w3id.org/tib/datacite/property/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?resource ?text ?titleType (LANG(?text) AS ?language)
WHERE {
  ?resource dcp:title ?title .
  ?title rdf:value ?text .
  OPTIONAL { ?title dcp:titleType ?titleType }
}
```

For creators, query their `schema:position` and sort numerically; RDF statement order carries no ordering guarantee. Polygon boundary points likewise use explicit positions. See `mappings/rdf-paths.json` for paths through structured elements rather than guessing paths from flat property names.

### Integrator guidelines

1. Keep the original metadata and the DataCite schema/modelling revision alongside converted output. The DOI and canonical term IRIs do not encode the model revision.
2. Pin the context, shapes and distribution to the same modelling revision for reproducible pipelines. Pin the JSON Schema to the corresponding DataCite schema version. Moving aliases are convenient when you deliberately accept upgrades.
3. Use absolute identifiers for URI-valued fields and preserve identifier scheme/value pairs. A URL-looking identifier remains text where DataCite defines an identifier, rather than a URI field.
4. Validate before and after conversion. Review warnings and preserve intentional extensions outside the DataCite RDF graph.
5. Test JSON-LD with a standards-compliant processor as well as the converter library. Term definitions may contain only JSON-LD-permitted entries; explanatory comments belong in documentation.
6. Treat `rdfs:range` as an inference statement, not validation. Use SHACL to check the delivered graph structure. OWL property-kind checks alone do not establish full reasoner conformance.
7. Migration from original 4.7 RDF to r2 requires queries to follow the linked value nodes and ordering properties. Do not mix older flat records and r2 shapes without an explicit migration.

---

## Crosswalk mappings

The four SSSOM files are the curated source. Each covers one target vocabulary on its own, so the sets may overlap (DCAT 3 reuses DCTERMS properties, for example). Subjects are canonical DataCite 4.7 IRIs (`https://w3id.org/tib/datacite/{property,class,vocab/<scheme>}/<name>`).

| File | Target |
|---|---|
| `datacite-schemaorg.sssom.tsv` | Schema.org 30.1 |
| `datacite-dcterms.sssom.tsv` | DCTERMS and DCMI Type |
| `datacite-dcat.sssom.tsv` | DCAT 3, including the DCTERMS terms it reuses. This is not a DCAT-AP conformance claim. |
| `datacite-wikidata.sssom.tsv` | Wikidata concept items (Q-items). Record-level statements are documented as conversion rules. |

Supporting files:

- **`conversion/<target>.json`** — declarative conversion rules for cases a term correspondence cannot express: inverse relations, node construction, qualifier-dependent targets and information loss. They are specifications, not an executable converter.
- **`coverage/<target>.json`** — one review outcome for every DataCite 4.7 term per target: `mapped`, `conversion_only`, `no_equivalent` or `out_of_scope`.
- **`target-vocabularies.json`** / **`target-sources.json`** — offline index of the pinned target vocabulary releases, used to reject undefined or deprecated target terms. Refresh it with `python3 rdf-build-scripts/update-mapping-target-inventory.py`.
- **`SKOS_crosswalks.jsonld`** and **`jskos-mappings.json`** — generated exports of the same triples, with term labels. Do not edit them by hand.
  - `jskos-mappings.json` is a JSON array of [JSKOS](https://gbv.github.io/jskos/) mappings ready for import into [jskos-server](https://github.com/gbv/jskos-server) and [Cocoda](https://coli-conc.gbv.de/cocoda/). Each mapping names its vocabularies by [BARTOC](https://bartoc.org/) URI (`fromScheme`/`toScheme`) and carries labels, creator, date, justification and the SSSOM comment as a note.
  - `SKOS_crosswalks.jsonld` is a self-contained JSON-LD graph: SKOS match links, `rdfs:label` for every term, and licence/creator/source metadata.

Each set's `mapping_set_id` is a persistent w3id IRI, e.g. `https://w3id.org/tib/datacite/mappings/datacite-schemaorg.sssom.tsv`. `generate-production-namespace.sh` copies the published mapping files into `production-namespace/mappings/`, and `npm run check:mappings` fails if that copy is out of date.

Mapping predicates are deliberately conservative. A `skos:relatedMatch` records an association, not permission to substitute one term for another; read the row comment and conversion rule before transforming records.

```bash
pip install -r rdf-build-scripts/requirements-mappings.txt
npm run build:mappings   # regenerate SKOS/JSKOS exports from SSSOM
npm run build:production-namespace   # refresh the published copy in production-namespace/mappings/
npm run check:mappings   # validate sources, coverage and exports without writing
npm run test:mappings    # regression tests
```

### Read match strengths and coverage correctly

| Predicate | Meaning from DataCite source to target | Conversion consequence |
|---|---|---|
| `skos:exactMatch` | Interchangeable concepts within the mapping's scope | Still inspect context and provenance; the Schema.org set deliberately asserts no exact matches |
| `skos:closeMatch` | Similar enough for some uses, but not guaranteed identical | Read the row comment and conversion rule |
| `skos:broadMatch` | The target meaning is broader than the source | Preserve the more specific DataCite meaning where needed |
| `skos:narrowMatch` | The target meaning is narrower than the source | Apply only when the record meets the narrower condition |
| `skos:relatedMatch` | Associated meanings | Does not authorize substituting one term for the other |

The four coverage outcomes are: `mapped` (a correspondence is asserted), `conversion_only` (a rule is needed), `no_equivalent` (no suitable target correspondence) and `out_of_scope` (outside that target set's declared purpose). Accounting for all source terms does not mean all terms have equivalents or that conversion is lossless.

A mapping connects **terms**; a conversion transforms **record values and nodes**. For example, a typed date may select a target date property, and an inverse relation may swap which resource is the subject. Never replace predicates mechanically from the TSV without reading those conditions. Wikidata Q-item alignments describe concepts; record statements using P-properties are a separate operation.

### Validate a JSKOS file

`validation-and-conversion/scripts/validate.js` validates JSKOS mappings, concepts, or schemes (a JSON array, a `{"mappings": [...]}` envelope, or NDJSON) using `jskos-validate`. It exits with a non-zero status if any item is invalid or unrecognised.

```bash
npm install
node validation-and-conversion/scripts/validate.js mappings/jskos-mappings.json
```

### Mapping contribution guidelines

Edit the SSSOM source for the target, then update that target's coverage and conversion rules. Use canonical source identifiers and terms from the pinned target inventory. Record the evidence, match strength, direction, author and actual reviewer. Naming the author again as reviewer does not establish independent review.

Test a concrete record example when a mapping depends on a role, identifier scheme, date kind or relation direction. State information loss and node placement. Update `mappings/rdf-paths.json` when the RDF structure changes. Generate SKOS/JSKOS and refresh the publication bundle; do not hand-edit the exports. The full change checklist is in [Contribution guidelines](#contribution-guidelines).

---

## Repository layout

The folders separate editable sources, conversion tools, generated output, and documentation:

| Path | What to expect |
|---|---|
| `production-namespace/` | Generated TIB/W3ID production bundle. This is the reviewable output intended for later sync to `TIBHannover/datacite-metadata-toolkit` and then publication through `TIBHannover/datacite`. It contains W3ID-rewritten `class/`, `property/`, `vocab/`, `context/`, `manifest/`, and `dist/` artifacts plus section `index.html` pages, the published `mappings/`, and the SHACL `shapes/`. It does not own publication-root files such as the root `README.md`, `.nojekyll`, `LICENSE`, or `index.html`; those belong to `TIBHannover/datacite`. |
| `rdf-vocabulary-staging/` | Editable linked-data source files. Despite the folder name, they use the canonical `https://w3id.org/tib/datacite/` IRIs. Expect class definitions, property definitions, controlled vocabularies, JSON-LD context files, manifests, generated distribution snapshots under `dist/`, and section index pages. |
| `rdf-build-scripts/` | Build and release tooling. This includes release detection/application scripts, manifest and distribution builders, index generation, production namespace generation, OWL generation, shared libraries, and templates copied into generated bundles. |
| `validation-and-conversion/` | The DataCite 4.7 JSON Schema, the DataCite 4.7 and 4.6 XSDs, XML validation and XML-to-JSON conversion scripts, the REST API JSON-to-RDF converter, SHACL shapes for its output, and example records. |
| `mappings/` | Curated SSSOM mapping sets from DataCite 4.7 terms to Schema.org, DCTERMS, DCAT 3, and Wikidata, with conversion rules, coverage records, and generated SKOS/JSKOS exports. |
| `tests/` | Automated regression tests for mappings, XML and JSON conversion, the JSON Schema, the SHACL shapes and the OWL files. |
| `prototypes/structured-values/` | Earlier before/after examples and comparison tools explaining the structured-value model. The maintained converter is in `validation-and-conversion/scripts/`. |
| `reports/` | Generated release detection/application reports and plans. These are regenerated by the release tooling. |
| `website/` | Source website pages used for human-facing documentation and landing pages. |
| `.github/workflows/` | GitHub Actions checks and release tooling. The Pages deployment and publication-sync files have a `.disabled` suffix in this source repository. |

---

## Namespace and resolvable IRIs

Every DataCite term has a permanent IRI under `https://w3id.org/tib/datacite/`. The source files in `rdf-vocabulary-staging/` use these IRIs directly, and each file's `@id` mirrors its location on disk, so a term's IRI is predictable from its folder:

| Resource | Canonical IRI |
|---|---|
| Class | `https://w3id.org/tib/datacite/class/<ClassName>` |
| Property | `https://w3id.org/tib/datacite/property/<propertyName>` |
| SKOS ConceptScheme | `https://w3id.org/tib/datacite/vocab/<scheme>` |
| SKOS Concept | `https://w3id.org/tib/datacite/vocab/<scheme>/<Term>` |
| JSON-LD context | `https://w3id.org/tib/datacite/context/fullcontext.jsonld` |
| Manifest | `https://w3id.org/tib/datacite/manifest/datacite-<version>.json` |

`generate-production-namespace.sh` builds the publication bundle from these sources. The separate publication repository serves its files through GitHub Pages:

| Layer | URL |
|---|---|
| Canonical persistent namespace | `https://w3id.org/tib/datacite/` |
| GitHub Pages publication backend | `https://tibhannover.github.io/datacite/` |

In that setup, RDF identifiers use w3id, while GitHub Pages serves the concrete files. For example, the canonical term IRI `https://w3id.org/tib/datacite/vocab/resourceTypeGeneral/Dataset` resolves through w3id to the file served at `https://tibhannover.github.io/datacite/vocab/resourceTypeGeneral/Dataset.jsonld`. A client that asks for Turtle (`Accept: text/turtle`) will get the `.ttl` file instead once perma-id/w3id.org#6828 is merged.

### Shared controlled lists

Two `relatedItem` sub-properties reuse the controlled vocabularies of other DataCite properties — per spec, **not** as parallel vocabularies. The JSON-LD context (`rdf-vocabulary-staging/context/fullcontext.jsonld`) reflects this by pointing both `@vocab` bases at the canonical scheme directories:

| Sub-property | Reuses list from | Spec reference |
|---|---|---|
| `relatedItemType` | `resourceTypeGeneral` (vocab/resourceTypeGeneral/) | [4.7 §20.a](https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/relateditem/): *"Use the controlled list values as stated in 10.a resourceTypeGeneral"* |
| `relatedItemIdentifierType` | `relatedIdentifierType` (vocab/relatedIdentifierType/) | [4.7 §20.1.a](https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/relateditem/): matches property 12.a exactly |

This means a value like `Dataset` appearing under `relatedItemType` resolves to the same SKOS Concept IRI as it would under `resourceTypeGeneral` (`…/vocab/resourceTypeGeneral/Dataset`). Consumers distinguish the two usages by the **predicate** (`property:relatedItemType` vs `property:resourceTypeGeneral`), not the object. This eliminates the maintenance hazard of keeping two parallel vocabularies in sync as new values are added (e.g. 4.7's `Poster`/`Presentation` automatically apply to both fields).

The following fields are **open lists** per spec — values are free text, not constrained to a controlled vocabulary. The context types them as `xsd:string`:

| Sub-property | Spec reference | Typical values |
|---|---|---|
| `alternateIdentifierType` | [4.7 §11.a](https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/alternateidentifier/) | Free text (e.g. Local accession number, Inventory number) |
| `subjectScheme` | [4.7 §6.a](https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/subject/) | Free text (e.g. LCSH, ANZSRC Fields of Research, MeSH) |
| `nameIdentifierScheme`, `affiliationIdentifierScheme`, `rightsIdentifierScheme`, `publisherIdentifierScheme` | various — recommended values, not strictly closed | ORCID, ROR, ISNI, SPDX, … |

---

## Versioning model

The DataCite metadata schema evolves over time (4.6, 4.7, …). This section explains how the linked-data vocabulary handles that change, so consumers always know exactly what they are pointing at.

There are three kinds of artifact, and they behave differently:

| Artifact | Example | Changes over time? | Use it when you want… |
|---|---|---|---|
| **Canonical term IRI** | `…/property/subject`, `…/vocab/resourceTypeGeneral/Dataset` | The identifier stays stable; its current definition can evolve | A durable identifier for a DataCite term |
| **Frozen versioned distribution** | `dist/datacite-4.6.ttl`, `dist/datacite-4.7.ttl` | Frozen after publication; documented correction exceptions are recorded in [Version history](#version-history) | The exact state of the vocabulary as of one release |
| **Moving "latest" distribution** | `dist/datacite.ttl` (`.jsonld`, `.rdf`) | Yes — always equals the newest release | Always-current vocabulary, from one stable URL |

A separate pointer file, `dist/datacite-current.jsonld`, is a small machine-readable record that simply names which release is currently the default.

**Key consequence — version provenance.** Because canonical term IRIs are stable, a machine *cannot* tell which DataCite schema version a term was used under from the IRI alone. If you dereference `…/property/subject`, you get its current meaning. If exact provenance matters (was this record built against 4.6 or 4.7?), the consuming system must store that separately — either the schema version string (e.g. `4.6`) or the versioned snapshot IRI (e.g. `…/dist/datacite-4.6.jsonld`).

### Revisions of one DataCite version

A *revision* changes how one DataCite version is modelled in RDF without changing its terms. `4.7-r2` is revision 2 of DataCite 4.7; versions sort as 4.7 < 4.7-r2 < 4.8. A revision gets its own frozen files (`manifest/datacite-4.7-r2.json`, `context/fullcontext-4.7-r2.jsonld`, `dist/datacite-4.7-r2.*`), and the files of the earlier revision stay unchanged except for a documented correction. Do not rebuild them from current term definitions.

**4.7-r2 changes the shape of DataCite RDF.** Each repeatable element (title, description, date, identifier, rights, ...) becomes its own node with its text in `rdf:value`, and creators carry `schema:position`. The moving `context/fullcontext.jsonld` and `dist/datacite.*` now follow 4.7-r2. To keep the 4.7 behaviour, use `context/fullcontext-4.7.jsonld` and `dist/datacite-4.7.*`.

### Why we do not mint versioned per-term IRIs

Several community members have asked for version-specific IRIs for individual *terms* (so a term carries its release inside its own identifier). We deliberately do **not** do this:

- **Identifier explosion.** Versioning every term on every release would create thousands of near-duplicate IRIs, and tools that reason about `sameAs` / `relatedTo` would have to reconcile all of them.
- **Aligns with DC / DCTERMS.** The established practice is to treat each major change as a new *ontology version*, not as new per-term IRIs.
- **Forward-compatible.** Frozen distributions don't rule out per-term versioned IRIs later; if a strong need emerges they can be layered on without breaking any existing stable IRI.

### Two separate versioning questions

These are easy to conflate but are independent:

1. **Which version of an *external* subject vocabulary was used?** (e.g. UAT 5.1, AGROVOC) — expressed in the Subject property's `schemeUri` when that vocabulary offers a versioned IRI. This is about *other people's* vocabularies, not DataCite's.
2. **Which version of the *DataCite* schema was used?** — a separate concern, captured by the versioned distribution / schema-version context described above.

See also [Version History](#version-history) for what changed in each release.

### Protecting frozen releases

A versioned filename is not enough to preserve history: older files must retain the definitions they contained at release time. The correction work adds checksum records in `rdf-build-scripts/frozen-releases.json` and a checker:

```bash
python3 rdf-build-scripts/check-frozen-releases.py
```

When a new current version replaces the old one, record the outgoing release's checksums as part of the reviewed release change:

```bash
python3 rdf-build-scripts/check-frozen-releases.py --record "PREVIOUS_VERSION"
```

`PREVIOUS_VERSION` is a placeholder for the outgoing revision. Recording checksums acknowledges the files currently on disk; it is not a repair for accidental modifications. Restore unintended changes before recording anything.

The snapshot command is for new versions; building an older distribution from current sources can change its meaning. The relevant commands refuse frozen rebuilds by default. An explicit `--rebuild-frozen` override is reserved for a reviewed correction with documented scope, preserved evidence and updated checksums. Never use the override merely to make a check pass.

The approved 7 October correction removes invalid `_note` entries from the original 4.7 context in place as well as the r2/current contexts. This is a JSON-LD syntax repair; it does not intentionally alter the RDF produced by permissive processors. It is recorded alongside the r2 corrections in [Version history](#version-history).

---

## Contribution guidelines

### Propose a change or report a bug

Use the [issue templates](https://github.com/TIBHannover/datacite-metadata-toolkit/issues/new/choose) for validation bugs, mapping requests and other changes. Include the tool/command, DataCite version, expected behaviour, actual message and a small reproducible example. Remove sensitive metadata before posting. General questions can go to [Discussions](https://github.com/selgebali/datacite-metadata-toolkit/discussions).

For code or documentation changes, create a branch, make the change in its maintained source and open a pull request against the appropriate toolkit repository. Generated namespace changes follow the [publication flow](#source-and-publication-flow).

### Choose the correct source

| Change | Maintained source | Refresh or verify |
|---|---|---|
| Term definition or controlled list | `rdf-vocabulary-staging/class/`, `property/`, `vocab/` | Context/manifest as applicable, JSON Schema lists, shapes, current distribution and bundle |
| JSON-LD representation | `rdf-vocabulary-staging/context/` and RDF converter | Language/value association, typing, ordering, context syntax and RDF paths |
| JSON validation rule | Current version's JSON Schema | `build-json-schema.py` refreshes controlled lists and the moving alias; review hand-written rules separately |
| RDF validation rule | Current revision's SHACL file outside generated markers | `build-shapes.py` refreshes the generated controlled-value section |
| XML conversion | `validation-and-conversion/scripts/convert.py` | Valid XML fixture through JSON and RDF, with preservation assertions |
| Crosswalk | SSSOM source, target coverage and conversion recipes | Generated SKOS/JSKOS, guide, publication copies and relevant tests |
| User guidance | This README and applicable `website/` pages | Commands, paths, anchors and agreement with actual behaviour |
| Public bundle | Upstream maintained sources and build templates | Rebuild `production-namespace/`; preserve publication-owned root files |

### Review principles

- **Use authoritative evidence.** Cite the DataCite prose specification and XSD where appropriate. If they disagree, name the discrepancy and the policy chosen, as for related-item titles.
- **Preserve information.** Test text, qualifiers, languages, nested entities and ordering together. A conversion that passes validation but drops a value is still wrong.
- **Test both acceptance and rejection.** Include valid omissions and invalid additions; test numeric and textual forms when both are supported.
- **Keep comparisons independent.** Matching two generated outputs can prove consistency while missing a shared mistake. Use an official specification, a second processor or an independently stated expected result where it matters.
- **Respect version boundaries.** Preserve old semantics and frozen artifacts. Document intentional corrections and migration effects.
- **Describe evidence precisely.** Do not claim all records, all mappings or zero false positives from a few passing examples. A corpus result needs a retrievable sample, selection method, script/version, date and classified outcomes.
- **Write for the next reader.** Define unfamiliar terms, give copyable examples and expected results, and state limitations beside the relevant command. Put implementation and release details in the maintainer sections.

### Checks before a pull request

After installing the quick-start dependencies, run the checks relevant to your change. The standard local review set is:

```bash
npm run test:conversion
npm run test:mappings
npm run check:json-schema
npm run check:shapes
npm run check:mappings
npm run check:current-aliases
npm run check:vocab-scheme-titles
python3 rdf-build-scripts/check-frozen-releases.py
```

The mapping workflow additionally validates each SSSOM set with the official validator:

```bash
sssom validate mappings/datacite-schemaorg.sssom.tsv -V JsonSchema -V PrefixMapCompleteness -V StrictCurieFormat
```

Run that check for all four `datacite-*.sssom.tsv` files when changing mappings. If `sssom` is not found, activate the virtual environment used to install `requirements-mappings.txt`.

Changes to generated artifacts also require the builds and checksum verification in [Build and publication](#build-and-publication). For context changes, verify expansion in a strict JSON-LD 1.1 processor such as PyLD in addition to RDFLib. For documentation changes, execute the affected commands, check links/anchors, and review the instructions from a fresh reader's starting point.

A pull request should explain the concrete problem, resulting behaviour, files/versions affected and validation performed. Name known limitations and publication work still pending. An implementation fix is complete locally only when its regression checks pass; publishing is a separate stage.

CI definitions are in [Check Mappings](https://github.com/selgebali/datacite-metadata-toolkit/actions/workflows/check-mappings.yml) and [Check Production Namespace](https://github.com/selgebali/datacite-metadata-toolkit/actions/workflows/check-production-namespace.yml). They run for changes matching each workflow's path filters. The workflow result is authoritative for that run; these checks do not certify every possible record or semantic correspondence.

## Build and publication

This section is for maintainers. Normal users can stop after validating and converting their records.

### Build the production bundle

Generate the public TIB/w3id namespace bundle:

```bash
npm run build:production-namespace
# Output is written to production-namespace/
```

The command copies the sources, which already use the canonical `https://w3id.org/tib/datacite/` IRIs, adds a Turtle file next to every term file, rebuilds the HTML index pages for the GitHub Pages project path `/datacite`, copies the published mappings and SHACL shapes, and writes a production-specific README into the bundle. It also writes `CHECKSUMS.sha256` and `manifest/bundle-integrity.json` so the file count and bundle checksum can be reviewed. The generated bundle is committed in this repository first so it can be reviewed and then synced to `TIBHannover/datacite-metadata-toolkit`; publication to `TIBHannover/datacite` happens from that TIB fork.

The production bundle intentionally does not own publication-root files such as the root `README.md`, `.nojekyll`, `LICENSE`, or `index.html`; those belong to `TIBHannover/datacite`.

To override the defaults:

```bash
CANONICAL_NAMESPACE="https://w3id.org/tib/datacite/" \
PAGES_BASE_PATH="/datacite" \
PUBLICATION_BASE_URL="https://tibhannover.github.io/datacite/" \
DST="production-namespace" \
bash rdf-build-scripts/generate-production-namespace.sh
```

For a vocabulary/model change, refresh the current distributions and OWL before assembling the bundle. Distribution generation requires Apache Jena's `riot`; OWL and term Turtle generation require the Python dependencies listed below. A mappings-only or documentation-only change need not rewrite frozen snapshots.

```bash
python -m pip install -r rdf-build-scripts/requirements-namespace.txt
python -m pip install -r rdf-build-scripts/generate-owl-file/requirements.txt
python3 rdf-build-scripts/generate-owl-file/generate-owl-file.py
npm run build:production-namespace
```

If the current RDF/OWL distribution needs regeneration from changed vocabulary definitions, use `node rdf-build-scripts/build-distribution.js --version 4.7-r2` for the current revision, then regenerate the `.owl` file and bundle. Do not use `release-snapshot.js` merely to refresh a published revision's manifest.

Building the bundle recreates its destination directory. Use the default generated destination or a dedicated temporary directory; do not point `DST` at a working source directory or the publication checkout. Commit/review the generated artifacts with the source change.

From a shell, verify the generated bundle:

```bash
(cd production-namespace && shasum -a 256 -c CHECKSUMS.sha256)
```

Expected result: every listed file reports `OK` and the command exits with status 0. `CHECKSUMS.sha256` and `manifest/bundle-integrity.json` exclude themselves from the artifact list; the integrity file records the checksum of the checksum list. Checksums detect file differences, not semantic correctness.

### Source and publication flow

Changes to the generated namespace move through pull requests in this order:

1. [`selgebali/datacite-metadata-toolkit`](https://github.com/selgebali/datacite-metadata-toolkit): edit the sources, run checks, and build `production-namespace/`.
2. [`TIBHannover/datacite-metadata-toolkit`](https://github.com/TIBHannover/datacite-metadata-toolkit): review and integrate the toolkit changes.
3. [`TIBHannover/datacite`](https://github.com/TIBHannover/datacite): review and publish the generated files through GitHub Pages, which serves the W3ID namespace.

GitHub Pages is disabled on both toolkit repositories and enabled on the publication repository. This repository's Pages deployment and publication-sync workflows are disabled; publication is a separate PR-based step.

Start generated namespace changes in a toolkit repository and rebuild the bundle rather than editing its generated files by hand. The publication repository owns its root `README.md`, `.nojekyll`, `LICENSE`, and `index.html`; preserve these when updating the generated files. After cloning or syncing the publication repository, run `shasum -a 256 -c CHECKSUMS.sha256` from its root to verify the actual publication tree.

### Verify publication

1. Finish source review and required checks; build the exact bundle intended for publication.
2. Integrate through the TIB toolkit fork and update the publication repository through its PR flow. Preserve its root-owned files.
3. Check the publication tree against the intended generated-file checksums and confirm the public current manifest, context, distributions, mappings, JSON Schema and shapes correspond to the approved release.
4. Verify concrete downloads and canonical identifiers separately. Check JSON-LD/Turtle content negotiation after the redirect change is merged; a working backend URL does not prove its w3id route works.
5. Update the dated [release status](#release-status) only after the public checks succeed. State any remaining redirect dependency and working fallback URLs.

## Release acceptance checklist

Use these fixed gates to finish the current correction release. Do not turn this release into a new exporter or vocabulary expansion project.

- [ ] **Context interoperability:** delivered contexts expand in RDFLib and a strict JSON-LD 1.1 processor; invalid context notes are removed, including the documented 4.7 correction.
- [ ] **Information preservation:** valid XML fixtures retain creator/contributor name languages, all polygons and inPolygonPoint values through JSON and RDF.
- [ ] **Validation policy:** related-item titles remain required with the XSD discrepancy explained; related-item identifier type remains optional; textless descriptions are accepted; funder identifier types, polygon minima and coordinate bounds in both number/text forms are enforced.
- [ ] **Diagnostics:** unknown JSON keys and empty identifiers warn with their source location; the beginner workflow validates JSON before conversion.
- [ ] **Reproducibility:** relevant regressions pass, generated artifacts match, checksums verify and frozen releases are protected; intentional corrections are documented.
- [ ] **Handoff:** the beginner walkthrough works, errors have recovery instructions, empirical claims have evidence or qualifications, dependency installation is reproducible, and code/data license texts are present.
- [ ] **Publication:** reviewed generated files are deployed and verified; canonical/backend URL status is accurately recorded.

Check a box only with evidence. A planned fix, an unmerged PR, a current-version pointer or a passing structural check is not proof that every gate is complete. Publication differences remain a release task until the approved files are served.

---

## Upgrading to a New DataCite Version

The release pipeline is **detect → review → apply**. Each step has a GitHub Actions workflow and a local Node command. The 4.6 → 4.7 plan shown below is a historical example, not an instruction to reapply a published release. For a new official release, use its actual version, date and generated plan path. Review the prose specification and XSD as well as the detected changes.

### Prerequisites

- Node.js 20+
- [Apache Jena](https://jena.apache.org/download/) (`riot` on PATH) — only needed for `build-distribution` / `release-snapshot`, which generate `.ttl` and `.rdf` files.

### Step 1 — Detect

**What it does:** Fetches the official DataCite schema release page, compares it to the local manifest versions, and writes a machine-readable JSON plan plus a Markdown report under `reports/`.

**Via GitHub Actions:**

1. Go to **Actions → Detect DataCite Release → Run workflow**
2. Optionally fill in the new official `version` and `release_date`. Leave both blank to auto-detect the next release.
3. Enable **Commit plan files** (default: on) to push the plan to the branch automatically.

**Locally:**

```bash
# Auto-detect next release
node rdf-build-scripts/detect-datacite-release.js

# Historical detection example (reads sources; it does not apply changes)
node rdf-build-scripts/detect-datacite-release.js --version 4.7 --release-date 2026-03-03
```

**Output files:**

| File | Description |
|---|---|
| `reports/release-import-plan-4.7.json` | Machine-readable change plan — edit this to approve/skip changes |
| `reports/release-import-plan-4.7.md` | Human-readable summary of detected changes |

### Step 2 — Review and approve the plan

Open `reports/release-import-plan-4.7.json`. Each detected change has a `"status"` field:

| Status | Meaning |
|---|---|
| `"proposed"` | Automatically detected; ready to approve |
| `"apply"` | **Change this from `"proposed"` to approve it for the next step** |
| `"skip"` | Intentionally excluded from this run |
| `"manual"` | Requires manual attention before it can be applied (e.g. renames, removals) |

Change every `"proposed"` entry you want to apply to `"apply"`. Entries left as `"proposed"` or `"manual"` are skipped.

**Typical 4.6 → 4.7 plan looks like:**

```jsonc
{
  "targetVersion": "4.7",
  "releaseDate": "2026-03-03",
  "changes": [
    {
      "id": "controlled-list-values-added:resourceTypeGeneral:4.7",
      "module": "controlled-list",
      "kind": "controlled-list-values-added",
      "status": "apply",       // ← set to "apply" to include
      "summary": "Add resourceTypeGeneral terms: Poster, Presentation"
    },
    {
      "id": "controlled-list-values-added:relatedIdentifierType:4.7",
      "module": "controlled-list",
      "status": "apply",
      "summary": "Add relatedIdentifierType terms: RAiD, SWHID"
    },
    {
      "id": "simple-property-added:relationTypeInformation:4.7",
      "module": "simple-property",
      "status": "apply",
      "summary": "Add simple property relationTypeInformation"
    }
  ]
}
```

### Step 3 — Apply

**What it does:** Reads the approved plan, writes new vocab term files into `rdf-vocabulary-staging/`, updates scheme files and `context/fullcontext.jsonld`, then builds a full versioned snapshot (manifest + dist bundles + index pages).

**Via GitHub Actions:**

1. Go to **Actions → Apply DataCite Release Plan → Run workflow**
2. Set `plan_path` to the reviewed plan for the new release; do not reapply the historical 4.7 plan.
3. Leave module toggles at their defaults unless you want to selectively run only some modules
4. Enable **Commit generated files** (default: on) to push all outputs back to the branch

**Locally:**

```bash

# Replace NEW_VERSION with the actual new release and review this plan first.
PLAN_PATH="reports/release-import-plan-NEW_VERSION.json"
node rdf-build-scripts/apply-datacite-release-plan.js \
  --plan "$PLAN_PATH" \
  --set-current
```

**What gets written (paths below illustrate the historical 4.7 plan):**

| Path | Description |
|---|---|
| `rdf-vocabulary-staging/vocab/<scheme>/<Term>.jsonld` | New term files |
| `rdf-vocabulary-staging/vocab/<scheme>/<scheme>.jsonld` | Updated scheme with new `hasTopConcept` entries |
| `rdf-vocabulary-staging/property/<name>.jsonld` | New property files (for simple-property changes) |
| `rdf-vocabulary-staging/context/fullcontext.jsonld` | Updated context mappings |
| `rdf-vocabulary-staging/manifest/datacite-4.7.json` | New versioned manifest |
| `rdf-vocabulary-staging/manifest/release-matrix-4.6-4.7.json` | Change delta between versions |
| `rdf-vocabulary-staging/manifest/datacite-current.json` | Updated current-version pointer |
| `rdf-vocabulary-staging/dist/datacite-4.7.{jsonld,ttl,rdf}` | Bundled distribution in 3 RDF formats |
| `rdf-vocabulary-staging/dist/datacite-current.jsonld` | Pointer to the current distribution |
| `rdf-vocabulary-staging/dist/datacite.{jsonld,ttl,rdf}` | Moving "latest" aliases |
| `rdf-vocabulary-staging/*/index.html` | Updated vocabulary browser index pages |
| `validation-and-conversion/schemas/schema-profiles/datacite-<version>.schema.json` and `datacite.schema.json` | JSON Schema with the new terms. A new DataCite version gets a new file, created from the previous one; review its hand-written rules against the release notes. |
| `validation-and-conversion/shapes/datacite-<version>.shacl.ttl` | SHACL shapes with the new terms; likewise a new file for a new version |
| `reports/release-apply-4.7.md` | Summary of what was applied |

### Snapshot a new version without a plan

A snapshot creates a **new** version from reviewed sources. Replace `NEW_VERSION` below with the actual new release or modelling revision; do not paste the placeholder unchanged. The new version must not already have a published distribution. For an official schema release, supply its official release date; for a modelling revision, supply the approved revision date.

```bash
node rdf-build-scripts/release-snapshot.js \
  --version "NEW_VERSION" \
  --release-date "YYYY-MM-DD"
```

The workflow equivalent is **Build Versioned Snapshot**, with the same new version/date. The script runs manifest sync, distribution generation, current pointers (unless `--no-set-current`), index pages, JSON Schema and shapes generation. Review every hand-written validation rule against the new schema; generated controlled lists alone are not a complete upgrade.

Do not snapshot 4.6 or another frozen version to refresh current files. Historical reproduction requires the historical source checkout. A deliberate correction follows the documented frozen-release policy; `--rebuild-frozen` is an explicit exception, not routine maintenance.

### Individual script reference

All scripts run from the repository root and auto-detect `rdf-vocabulary-staging/` as the vocabulary root.

| Script | Usage | Description |
|---|---|---|
| `manifest-sync.js` | `--check \| --write \| --validate [--version x.y] [--manifest <path>] [--allow-narrow]` | Rebuilds or validates a manifest from files on disk |
| `build-distribution.js` | `[--version x.y] [--rebuild-frozen]` | Bundles the selected manifest using current term definitions; refuses older published versions by default |
| `update-current-pointers.js` | `[--version x.y]` | Writes `datacite-current.json` and `dist/datacite.jsonld` aliases |
| `check_live_sample.py` | `--size N [--save FILE]` | Exploratory public API validation; save the corpus before citing results (script is in `validation-and-conversion/scripts/`) |
| `check-current-aliases.js` | — | Fails if `dist/datacite.{jsonld,ttl,rdf}` differ from the current version's files (`npm run check:current-aliases`) |
| `generate-index-pages.js` | _(no args)_ | Regenerates HTML browser index pages for `class/`, `property/`, `vocab/`, `context/`, `dist/`, `manifest/` |
| `generate-production-namespace.sh` | env vars: `CANONICAL_NAMESPACE`, `PAGES_BASE_PATH`, `PUBLICATION_BASE_URL`, `DST` | Builds the reviewable `production-namespace/` bundle for the TIB/W3ID publication flow |
| `update-root-index.js` | _(no args)_ | Patches AUTO marker blocks in `rdf-vocabulary-staging/index.html` if that file exists (no-op otherwise) |
| `detect-datacite-release.js` | `[--version x.y] [--release-date YYYY-MM-DD]` | Detects changes, writes plan to `reports/` |
| `apply-datacite-release-plan.js` | `--plan <path> [--modules <csv>] [--set-current]` | Applies an approved plan to vocab source files |
| `release-snapshot.js` | `--version x.y [--release-date YYYY-MM-DD] [--no-set-current] [--rebuild-frozen]` | New-version snapshot; refuses already published versions by default |
| `check-frozen-releases.py` | `[--record VERSION]` | Verifies checksums of frozen releases; recording is for a reviewed baseline/correction |
| `build-json-schema.py` | `[--check]` | Writes `datacite-<version>.schema.json` and `datacite.schema.json` for the current version, with controlled lists from the vocabulary files (`npm run check:json-schema`) |
| `build-shapes.py` | `[--check]` | Writes the controlled-value shapes of the current version's SHACL file from the vocabulary files (`npm run check:shapes`) |

**Module IDs** (for `--modules` CSV in apply):

| ID | What it handles |
|---|---|
| `controlled-list` | Adds new terms to vocab schemes and creates term `.jsonld` files |
| `simple-property` | Creates a new property `.jsonld` and adds its context entry |
| `property-group` | Creates a group of related properties with shared context entries |
| `complex-structure` | Creates new class + property files for a complex nested structure |
| `rename` | Renames a controlled-list term |
| `removal` | Removes deprecated terms or context entries |

---

## Version History

`rdf-vocabulary-staging/manifest/datacite-current.json` points at the current revision in this repository (currently **4.7-r2**). It does not confirm which revision is deployed on the public site. Schema-release tooling produces versioned manifests, apply reports under `reports/`, and release-matrix deltas; modelling revisions also have their own versioned manifests and distributions.

### DataCite 4.7-r2 (current)

Revision 2 of the DataCite 4.7 modelling: same terms, a new RDF shape. It is a breaking change for RDF data; see [Revisions of one DataCite version](#revisions-of-one-datacite-version).

- Repeatable elements become their own nodes, with the element's text in `rdf:value` and its qualifiers beside it. Fourteen link properties gain an `rdfs:range` and a `skos:scopeNote` saying where the text goes.
- Creators and polygon points record their order with `schema:position` (1 = first).
- SHACL shapes (`shapes/datacite-4.7-r2.shacl.ttl`) check DataCite RDF against these rules.
- `mappings/rdf-paths.json` gives the SPARQL path to every DataCite term in this RDF.
- The converter retains alternate identifiers without mistaking a distinct DOI for the record's own DOI, and normalizes string affiliations into value nodes.
- Crosswalk recipes cover additional DCAT relationships, DCTERMS `IsSourceOf`, and Schema.org `ComputationalNotebook` mappings.

Corrections prepared on 7 October 2026 bring the context and OWL files into line with the documented r2 conventions. They still follow the review/publication process; this history does not assert that every correction is already served publicly:

- `affiliationIdentifier`, `publisherIdentifier` and `funderIdentifier` are always text (`xsd:string`). Before, a value that was a web address became a link and any other value became text, so one property held two kinds of value.
- Coordinates are typed `xsd:float` (as in the DataCite XSD) and `publicationYear` `xsd:gYear`. Before, they were numbers or text depending on how the record wrote them.
- The OWL files declare each property as `owl:DatatypeProperty` (text and numbers) or `owl:ObjectProperty` (nodes and links). Before, every property was declared an object property, so text and numbers appeared on object properties, which OWL 2 DL does not allow and which OWL reasoners therefore reject.
- The SHACL shapes check every controlled value against the full list of its vocabulary's terms, and check the identifier, coordinate and year datatypes.

Additional local corrections in the current PR:

- Remove the two invalid `_note` entries from the current, r2 and original 4.7 contexts. The original 4.7 context is corrected in place as an explicit frozen-file exception. Removing explanatory notes repairs JSON-LD syntax without intentionally changing RDF output.
- Preserve XML name languages, multiple polygons and interior polygon points.
- Make related-item identifier type optional, require funder identifier type when its value is supplied, and enforce polygon point minima and coordinate bounds in supported numeric/text representations.
- Accept descriptions with a type but no text, as the XSD permits.
- Keep related-item titles required because the prose documentation states 1–n; explain that the XSD leaves them optional.
- Warn about unknown JSON keys, protect published snapshots and qualify the exploratory API-sample claim.

### DataCite 4.7

Applied on top of 4.6 via the Detect → Review → Apply pipeline. Changes:

- **`resourceTypeGeneral`**: adds **`Poster`**, **`Presentation`**
- **`relatedIdentifierType`**: adds **`RAiD`**, **`SWHID`**
- **`relationType`**: adds **`Other`**
- New property **`relationTypeInformation`** (additional information about the selected relationType, applies to both `relatedIdentifier` and `relatedItem`)

Not a 4.7 change, but worth knowing: since `relatedItem` was introduced in 4.4, DataCite advises giving series information as a `relatedItem` with `relationType=IsPublishedIn` rather than as a description with `descriptionType=SeriesInformation`. The term remains valid; see the scope note in [vocab/descriptionType/SeriesInformation.jsonld](rdf-vocabulary-staging/vocab/descriptionType/SeriesInformation.jsonld).

See `reports/release-apply-4.7.md` and `rdf-vocabulary-staging/manifest/release-matrix-4.6-4.7.json` for the full apply record.

### DataCite 4.6

Adds or updates these controlled values, all represented in the vocabulary files:

| Field | New values |
|---|---|
| `resourceTypeGeneral` | `Project`, `Award` |
| `relatedIdentifierType` | `RRID`, `CSTR` |
| `contributorType` | `Translator` |
| `relationType` | `IsTranslationOf`, `HasTranslation` |
| `dateType` | `Coverage` |

The `subject` sub-property **`classificationCode`**, for subject schemes such as ANZSRC that lack per-term `valueURI`s, dates from 4.4 and is included in the vocabulary.

---

## Key Concepts

**DOI** — A Digital Object Identifier for a research output. The record describes the output; the DOI identifies it.

**IRI** — An Internationalized Resource Identifier: the globally unique web-style identifier used for a resource or term.

**RDF / Turtle** — RDF represents data as subject–predicate–object statements. Turtle is the text format written by the RDF converter.

**Controlled vocabulary** — A defined set of allowed values, such as `Dataset` and `Software`. An open list instead permits free text.

**Crosswalk** — A documented correspondence between vocabularies. It can guide conversion but does not itself transform a record.

**JSON-LD** — A JSON-based format for linked data. An `@context` maps compact JSON keys to globally unique IRIs so different systems interpret the same key identically.

**SKOS** — The W3C Simple Knowledge Organization System. Used here to define controlled vocabulary terms and to map DataCite terms to equivalent terms in Schema.org, DCAT, and other vocabularies.

**JSKOS** — A JSON-based serialization of SKOS, used for interoperable mapping registries such as Cocoda.

**SSSOM** — The Simple Standard for Sharing Ontology Mappings. A TSV-based format that records each alignment between two terms with a predicate, justification, and provenance. The `.sssom.tsv` files in `mappings/` can be loaded directly by tools such as [sssom-py](https://mapping-commons.github.io/sssom-py/) or imported into ontology alignment pipelines.

**JSON Schema vs JSON-LD context** — The JSON Schema (`validation-and-conversion/schemas/schema-profiles/datacite.schema.json`) checks the *structure* of a JSON record (required fields, allowed values, data types). The JSON-LD context (`rdf-vocabulary-staging/context/fullcontext.jsonld`) gives those fields *semantic meaning* as linked data. Both can be applied to the same JSON document.

**SHACL** — The W3C Shapes Constraint Language. A SHACL file describes what valid RDF looks like; a validator such as pyshacl compares RDF data against it and reports every difference.

**OWL** — The W3C Web Ontology Language. The `*-owl*` and `.owl` files describe the same vocabulary for ontology tools such as Protégé.

**Source files vs publication bundle** — The source files in `rdf-vocabulary-staging/` and the generated `production-namespace/` bundle use the same `https://w3id.org/tib/datacite/` IRIs. The bundle adds Turtle copies, index pages, mappings, shapes and checksums, and is what TIB publishes.

---

## References

- [DataCite Metadata Schema 4.7](https://datacite-metadata-schema.readthedocs.io/en/4.7/)
- [DataCite Metadata Schema 4.7 XSD](https://schema.datacite.org/meta/kernel-4.7/)
- [DataCite Metadata Schema 4.6](https://schema.datacite.org/meta/kernel-4.6/)
- [DataCite REST API](https://support.datacite.org/docs/api)
- [JSON-LD specification](https://json-ld.org/)
- [JSON Schema specification](https://json-schema.org/)
- [SKOS Primer](https://www.w3.org/TR/skos-primer/)
- [JSKOS format](https://gbv.github.io/jskos/)
- [SSSOM specification](https://mapping-commons.github.io/sssom/)
- [SHACL specification](https://www.w3.org/TR/shacl/)

---

## License

- **Code** (scripts, tests, build tooling): Apache License 2.0, in [`LICENSE-CODE`](LICENSE-CODE).
- **Vocabulary, distributions, schemas, shapes and mapping sets:** Creative Commons Attribution 4.0 International, in [`LICENSE`](LICENSE). Each mapping set also names its licence in its header.

External vocabularies retain their own licenses and attribution requirements.
