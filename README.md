# DataCite Metadata Toolkit

This toolkit helps turn **DataCite metadata**—information describing research outputs—into **linked data** that other systems can understand. It provides definitions for metadata fields, tools for validating and converting records, and crosswalks to Schema.org, Dublin Core (DCTERMS), DCAT 3, and Wikidata.

The toolkit targets DataCite Metadata Schema **4.7** and keeps the earlier 4.6 files for reference. Its current linked-data modelling revision is **4.7-r2**: a second way of representing DataCite 4.7 in RDF, not a new DataCite schema release.

## Quick start

You need Python 3.9 or later, Node.js 20 or later, and a copy of this repository (`git clone https://github.com/selgebali/datacite-metadata-toolkit.git`, then `cd datacite-metadata-toolkit`). Install the dependencies once, preferably inside a Python virtual environment:

```bash
python3 -m pip install -r rdf-build-scripts/requirements-mappings.txt
```

```bash
npm install
```

Then check a DataCite record, turn it into linked data, and check the result. These commands use an example record that comes with the toolkit; replace the file name with your own record.

```bash
npm run --silent validate:json -- validation-and-conversion/examples/real-dataset-dryad.json
```

```bash
npm run --silent convert:rdf -- validation-and-conversion/examples/real-dataset-dryad.json > record.ttl
```

```bash
python3 -m pyshacl -s validation-and-conversion/shapes/datacite-4.7-r2.shacl.ttl record.ttl
```

Expected results: the first command prints `… valid`; the second writes `record.ttl` and prints nothing (or `warning:` lines for parts it had to leave out); the third prints `Conforms: True`.

**When a check fails**, it names the place in the record and the rule. For example, `validate:json` prints `record.json invalid`, followed by:

```text
instancePath: '/data/attributes/contributors/0',
message: "must have required property 'contributorType'"
```

`contributors/0` is the first contributor (counting starts at 0), and it needs a `contributorType`, such as `"contributorType": "DataCurator"`. A second entry, `must match "then" schema`, only says that the record as a whole failed, so ignore it. Fix the record and run the command again. Run the JSON check before converting: the converter leaves out keys it does not know, such as a misspelt `titel`, and the RDF check cannot see what is no longer there.

### What the toolkit does

| Task | Status |
|---|---|
| Check DataCite XML against the official 4.7 XSD | Works (`validate_xml.rb`, or `xmllint`) |
| Convert DataCite XML to REST API JSON | Works (`convert.py`) |
| Check REST API JSON against DataCite 4.7 | Works (`validate:json`) |
| Convert REST API JSON to DataCite RDF, and check the RDF | Works (`convert:rdf`, SHACL shapes) |
| Crosswalks to Schema.org, Dublin Core, DCAT and Wikidata | Documented mappings and conversion recipes; there is no converter that writes those formats |

Each check covers a different layer:

| Check | What it catches |
|---|---|
| XSD (XML) | The official DataCite rules for XML records |
| JSON Schema (REST API JSON) | Missing required properties, unknown or misspelt keys, values outside the controlled lists, empty identifiers, out-of-range coordinates, too-short polygons |
| SHACL shapes (RDF) | The structure of the RDF: one text per node, identifiers as text, creators and polygon points in order, controlled values from the DataCite vocabularies, datatypes |

None of them checks that a date is a real date, that an identifier resolves, or that the description is true.

## Current state

Titles, descriptions, dates, identifiers, and other repeatable elements are separate RDF nodes, so each value stays beside its own type, language, or other details. Creator order and polygon drawing order are recorded explicitly. Every DataCite term has a permanent address under `https://w3id.org/tib/datacite/`.

**Compatibility:** 4.7-r2 changes the structure of RDF records. Existing queries and converters written for the older structure may need updating. The earlier versioned distributions remain available; use `context/fullcontext-4.7.jsonld` and `dist/datacite-4.7.*` to retain the 4.7 behaviour. The unversioned context and distribution files follow 4.7-r2.

**Checks:** every pull request runs the regression tests, the mapping checks, and a rebuild of the publication bundle that must match the committed files. See the latest [Check Mappings](https://github.com/selgebali/datacite-metadata-toolkit/actions/workflows/check-mappings.yml) and [Check Production Namespace](https://github.com/selgebali/datacite-metadata-toolkit/actions/workflows/check-production-namespace.yml) runs. These checks cover the tested examples and structural rules; they do not establish that every possible record or crosswalk is correct.

**Publication status, checked 7 October 2026:** 4.7-r2 is published at `https://w3id.org/tib/datacite/`. The mapping sets (`mappings/`) and SHACL shapes (`shapes/`) are already on the GitHub Pages backend, but their w3id addresses return "Not Found" until [perma-id/w3id.org#6828](https://github.com/perma-id/w3id.org/pull/6828) is merged. Until then, use `https://tibhannover.github.io/datacite/mappings/…` and `…/shapes/…`.

## Source and publication flow

Changes to the generated namespace move through pull requests in this order:

1. [`selgebali/datacite-metadata-toolkit`](https://github.com/selgebali/datacite-metadata-toolkit): edit the sources, run checks, and build `production-namespace/`.
2. [`TIBHannover/datacite-metadata-toolkit`](https://github.com/TIBHannover/datacite-metadata-toolkit): review and integrate the toolkit changes.
3. [`TIBHannover/datacite`](https://github.com/TIBHannover/datacite): review and publish the generated files through GitHub Pages, which serves the W3ID namespace.

GitHub Pages is disabled on both toolkit repositories and enabled on the publication repository. This repository's Pages deployment and publication-sync workflows are disabled; publication is a separate PR-based step.

Start generated namespace changes in a toolkit repository and rebuild the bundle rather than editing its generated files by hand. The publication repository owns its root `README.md`, `.nojekyll`, `LICENSE`, and `index.html`; preserve these when updating the generated files. After cloning or syncing the publication repository, run `shasum -a 256 -c CHECKSUMS.sha256` from its root to verify the actual publication tree.

---

## Repository Layout

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

Three related fields are **open lists** per spec — values are free text, not constrained to a controlled vocabulary. The context types them as `xsd:string`:

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
| **Canonical term IRI** | `…/property/subject`, `…/vocab/resourceTypeGeneral/Dataset` | **Never** — stable forever | A durable identifier for a DataCite term |
| **Frozen versioned distribution** | `dist/datacite-4.6.ttl`, `dist/datacite-4.7.ttl` | **Never** after publication. Documented exceptions, 7 October 2026: the 4.7-r2 corrections (made before r2 was announced) and the removal of two invalid `_note` entries from the 4.7 context (no change in output); see [Version History](#version-history) | The exact state of the vocabulary as of one release |
| **Moving "latest" distribution** | `dist/datacite.ttl` (`.jsonld`, `.rdf`) | Yes — always equals the newest release | Always-current vocabulary, from one stable URL |

A separate pointer file, `dist/datacite-current.jsonld`, is a small machine-readable record that simply names which release is currently the default.

**Key consequence — version provenance.** Because canonical term IRIs are stable, a machine *cannot* tell which DataCite schema version a term was used under from the IRI alone. If you dereference `…/property/subject`, you get its current meaning. If exact provenance matters (was this record built against 4.6 or 4.7?), the consuming system must store that separately — either the schema version string (e.g. `4.6`) or the versioned snapshot IRI (e.g. `…/dist/datacite-4.6.jsonld`).

### Revisions of one DataCite version

A *revision* changes how one DataCite version is modelled in RDF without changing its terms. `4.7-r2` is revision 2 of DataCite 4.7; versions sort as 4.7 < 4.7-r2 < 4.8. A revision gets its own frozen files (`manifest/datacite-4.7-r2.json`, `context/fullcontext-4.7-r2.jsonld`, `dist/datacite-4.7-r2.*`), and the files of the earlier revision stay unchanged.

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

---

## How to Use

### 1. Explore the vocabulary

Start with `rdf-vocabulary-staging/manifest/datacite-current.json` to see the current revision, then open `rdf-vocabulary-staging/manifest/datacite-4.7-r2.json` for its index of classes, properties, and vocabulary terms. Earlier versioned manifests describe the earlier snapshots.

Individual term files follow a predictable structure:

- **Class files** (`class/Resource.jsonld`) — define the IRI, `rdf:type`, `rdfs:label`, and `rdfs:comment` for a DataCite entity.
- **Property files** (`property/identifier.jsonld`) — define the IRI and (where applicable) domain/range for a DataCite metadata field.
- **Vocab term files** (`vocab/resourceTypeGeneral/Dataset.jsonld`) — define a controlled term with `skos:prefLabel`, `skos:definition`, `skos:inScheme`, and optional `skos:closeMatch` mappings.

### 2. Use the JSON-LD context

`rdf-vocabulary-staging/context/fullcontext.jsonld` maps the keys of DataCite REST API JSON to their full IRIs. Reference it in your JSON-LD documents:

```json
{
  "@context": "https://w3id.org/tib/datacite/context/fullcontext.jsonld",
  "@id": "https://doi.org/10.1234/example",
  "titles": [{ "title": "Example title", "titleType": "Subtitle" }],
  "creators": [{ "name": "Smith, Jane", "nameType": "Personal" }]
}
```

Each title and creator becomes its own node: the title text is in `rdf:value` beside its `titleType`, and the name is in `creatorName`. A context alone cannot add node types, language tags or creator positions, so use the converter for complete RDF:

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

The SHACL shapes check these conventions: text in `rdf:value`, exactly once; identifiers as text; coordinates and years with their datatypes; creators and polygon points numbered with `schema:position`; and every controlled value a real term of its DataCite vocabulary, so a misspelling such as `IsCitedby` is reported. The controlled-value part of the shapes is generated from the vocabularies by `python3 rdf-build-scripts/build-shapes.py`.

### 3. Validate a DataCite XML record

`validation-and-conversion/scripts/validate_xml.rb` validates an XML file against DataCite's official 4.7 XSD (`schemas/xsd/4.7/`). Pass `--xsd validation-and-conversion/schemas/xsd/4.6/metadata.xsd` to check against 4.6 instead. Requires Ruby and the `nokogiri` gem (`gem install nokogiri`).

```bash
ruby validation-and-conversion/scripts/validate_xml.rb validation-and-conversion/examples/datacite-example-full-v4.xml
```

Without Ruby, `xmllint` gives the same result: `xmllint --noout --schema validation-and-conversion/schemas/xsd/4.7/metadata.xsd record.xml`.

### 4. Convert DataCite XML to REST API JSON

`validation-and-conversion/scripts/convert.py` parses a DataCite XML file and produces a JSON payload matching the DataCite REST API structure (a `data.attributes` envelope), including the 4.7 `relationTypeInformation`. Python 3 only — no external packages required.

```bash
python3 validation-and-conversion/scripts/convert.py \
    validation-and-conversion/examples/datacite-example-full-v4.xml \
    --output record.json
```

### 5. Validate JSKOS mappings

`validation-and-conversion/scripts/validate.js` validates JSKOS mappings, concepts, or schemes (a JSON array, a `{"mappings": [...]}` envelope, or NDJSON) using `jskos-validate`. It exits with a non-zero status if any item is invalid or unrecognised.

```bash
npm install
node validation-and-conversion/scripts/validate.js mappings/jskos-mappings.json
```

### 6. Generate the production namespace

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

### 7. Validate a REST API JSON record

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

See [JSON Schema](#json-schema) below for what it checks.

### 8. Explore crosswalk mappings

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

---

## JSON Schema

The JSON Schema (draft 2020-12) describes DataCite DOI records as the REST API returns and accepts them. It comes in two forms, like the vocabulary downloads:

| File | Changes over time? | Use it when you want… |
|---|---|---|
| `datacite-4.7.schema.json` (one per DataCite version) | No, once its version is no longer current | The rules of one DataCite release |
| `datacite.schema.json` | Yes, always equals the current version's file | The newest rules, from one stable address |

Once published, both resolve at their `$id`, for example `https://w3id.org/tib/datacite/schema-profiles/datacite.schema.json` (the w3id address works after perma-id/w3id.org#6828 is merged; the files are served from `https://tibhannover.github.io/datacite/schema-profiles/`).

- **Required:** `doi`, at least one creator with a name, at least one title, `publisher`, `publicationYear` and `types.resourceTypeGeneral`, as DataCite requires for a registered DOI.
- **Controlled values:** every controlled list (`resourceTypeGeneral`, `relationType`, `contributorType`, ...) is generated from the vocabulary files by `python3 rdf-build-scripts/build-json-schema.py`, using the spelling the REST API uses (for example `Crossref Funder ID`). When a DataCite release adds terms, the release tooling adds the vocabulary files and this script carries them into the schema; `npm run check:json-schema` fails if they disagree.
- **4.7 additions:** `Poster` and `Presentation`, `RAiD` and `SWHID`, relation type `Other`, and `relationTypeInformation` on related identifiers and related items.
- **REST API fields** that are not DataCite metadata (`url`, `state`, `viewCount`, `created`, ...) are accepted without checks. Null values are accepted for optional fields, as the REST API returns them.

`npm run --silent check:live-sample -- --size 300` fetches randomly chosen findable DOIs from the public REST API and runs the JSON Schema, the converter and the SHACL shapes on each, printing the problems found with an example DOI for each kind. On 7 October 2026, a run over 300 DOIs flagged 18 records. Every flagged problem was checked against the DataCite 4.7 XSD and documentation, and each was a real problem in the record: contributors without a name, empty titles, empty related identifiers and name identifiers, the retired contributor type `Funder`, and a missing `resourceTypeGeneral`. The sample is random, so results differ from run to run, and one sample cannot prove there are no false alarms. If a record that follows the DataCite rules is rejected, please report the DOI.

**Rules stricter than the DataCite XSD.** The schema rejects empty titles, creator names, subjects, dates and identifiers, which the XSD accepts but which carry no information. It also requires related-item titles, which the DataCite documentation makes mandatory but the XSD does not enforce. Each such field says so in its description in the schema.

The schema checks structure and values, not meaning: it does not check that a date is a real date or that an identifier resolves. For linked data, use the JSON-LD context and the converter described above.

The earlier 4.6 profiles are kept, unmaintained, in `schema-profiles/legacy-4.6/`.

---

## Upgrading to a New DataCite Version

The release pipeline is a three-step process: **detect → review → apply**. All three steps have both a GitHub Actions workflow (for CI) and a local Node.js command (for development).

### Prerequisites

- Node.js 20+
- [Apache Jena](https://jena.apache.org/download/) (`riot` on PATH) — only needed for `build-distribution` / `release-snapshot`, which generate `.ttl` and `.rdf` files.

### Step 1 — Detect

**What it does:** Fetches the official DataCite schema release page, compares it to the local manifest versions, and writes a machine-readable JSON plan plus a Markdown report under `reports/`.

**Via GitHub Actions:**

1. Go to **Actions → Detect DataCite Release → Run workflow**
2. Optionally fill in `version` (e.g. `4.7`) and `release_date` (e.g. `2026-03-03`). Leave both blank to auto-detect the next release.
3. Enable **Commit plan files** (default: on) to push the plan to the branch automatically.

**Locally:**

```bash
# Auto-detect next release
node rdf-build-scripts/detect-datacite-release.js

# Target a specific version
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
2. Set `plan_path` to `reports/release-import-plan-4.7.json`
3. Leave module toggles at their defaults unless you want to selectively run only some modules
4. Enable **Commit generated files** (default: on) to push all outputs back to the branch

**Locally:**

```bash
node rdf-build-scripts/apply-datacite-release-plan.js \
  --plan reports/release-import-plan-4.7.json \
  --set-current
```

**What gets written:**

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

### Published releases are frozen

Once a version is published, its manifest, context and distribution files must not change: other systems rely on them. The scripts protect them:

- `release-snapshot.js` refuses a version that already has distribution files. It is for new versions only.
- `build-distribution.js` refuses to rebuild a published version other than the current one, because it reads the *current* term files and would give the old release the current definitions.
- `npm run check:frozen-releases` (also run in CI) compares the files of every earlier version with the checksums in `rdf-build-scripts/frozen-releases.json` and fails if any changed.

To correct the **current** version, edit its source files and run `node rdf-build-scripts/build-distribution.js --version <current>`, then rebuild the production namespace. When a new version becomes current, record the one it replaces with `python3 rdf-build-scripts/check-frozen-releases.py --record <previous version>`. Both scripts accept `--rebuild-frozen` for a deliberate, documented exception.

**What a snapshot runs:** `manifest-sync --write --validate` → `build-distribution` → `update-current-pointers` → `generate-index-pages` → `update-root-index` → `build-json-schema.py` → `build-shapes.py`. The last two carry new vocabulary terms into the JSON Schema and the SHACL shapes of the new version.

### Individual script reference

All scripts run from the repository root and auto-detect `rdf-vocabulary-staging/` as the vocabulary root.

| Script | Usage | Description |
|---|---|---|
| `manifest-sync.js` | `--check \| --write \| --validate [--version x.y] [--manifest <path>] [--allow-narrow]` | Rebuilds or validates a manifest from files on disk |
| `build-distribution.js` | `[--version x.y]` | Bundles vocab files into `dist/datacite-<v>.jsonld` and converts to `.ttl`/`.rdf` |
| `update-current-pointers.js` | `[--version x.y]` | Writes `datacite-current.json` and `dist/datacite.jsonld` aliases |
| `check-current-aliases.js` | — | Fails if `dist/datacite.{jsonld,ttl,rdf}` differ from the current version's files (`npm run check:current-aliases`) |
| `generate-index-pages.js` | _(no args)_ | Regenerates HTML browser index pages for `class/`, `property/`, `vocab/`, `context/`, `dist/`, `manifest/` |
| `generate-production-namespace.sh` | env vars: `CANONICAL_NAMESPACE`, `PAGES_BASE_PATH`, `PUBLICATION_BASE_URL`, `DST` | Builds the reviewable `production-namespace/` bundle for the TIB/W3ID publication flow |
| `update-root-index.js` | _(no args)_ | Patches AUTO marker blocks in `rdf-vocabulary-staging/index.html` if that file exists (no-op otherwise) |
| `detect-datacite-release.js` | `[--version x.y] [--release-date YYYY-MM-DD]` | Detects changes, writes plan to `reports/` |
| `apply-datacite-release-plan.js` | `--plan <path> [--modules <csv>] [--set-current]` | Applies an approved plan to vocab source files |
| `release-snapshot.js` | `--version x.y [--release-date YYYY-MM-DD] [--no-set-current]` | Full snapshot: manifest-sync + dist + pointers + index pages |
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

Corrections made on 7 October 2026, before the revision was announced. They bring the context and the OWL files in line with the conventions 4.7-r2 already documented:

- `affiliationIdentifier`, `publisherIdentifier` and `funderIdentifier` are always text (`xsd:string`). Before, a value that was a web address became a link and any other value became text, so one property held two kinds of value.
- Coordinates are typed `xsd:float` (as in the DataCite XSD) and `publicationYear` `xsd:gYear`. Before, they were numbers or text depending on how the record wrote them.
- The OWL files declare each property as `owl:DatatypeProperty` (text and numbers) or `owl:ObjectProperty` (nodes and links). Before, every property was declared an object property, so text and numbers appeared on object properties, which OWL 2 DL does not allow and which OWL reasoners therefore reject.
- The SHACL shapes check every controlled value against the full list of its vocabulary's terms, and check the identifier, coordinate and year datatypes.
- Two explanatory `_note` entries were removed from the JSON-LD context. JSON-LD 1.1 does not allow them inside term definitions, so standards-compliant processors (PyLD, jsonld.js) rejected the whole context. The same two entries were also removed from the frozen 4.7 context, `context/fullcontext-4.7.jsonld`. These removals change no RDF output.

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

- DataCite Metadata Schema 4.7 — https://datacite-metadata-schema.readthedocs.io/en/4.7/
- DataCite Metadata Schema 4.7 XSD — https://schema.datacite.org/meta/kernel-4.7/
- DataCite Metadata Schema 4.6 — https://schema.datacite.org/meta/kernel-4.6/
- DataCite REST API — https://support.datacite.org/docs/api
- JSON-LD specification — https://json-ld.org/
- JSON Schema specification — https://json-schema.org/
- SKOS Primer — https://www.w3.org/TR/skos-primer/
- JSKOS format — https://gbv.github.io/jskos/
- SSSOM specification — https://mapping-commons.github.io/sssom/
- SHACL specification — https://www.w3.org/TR/shacl/

---

## License

- **Code** (scripts, tests, build tooling): Apache License 2.0, in [`LICENSE-CODE`](LICENSE-CODE).
- **Vocabulary, distributions, schemas, shapes and mapping sets:** Creative Commons Attribution 4.0 International, in [`LICENSE`](LICENSE). Each mapping set also names its licence in its header.
