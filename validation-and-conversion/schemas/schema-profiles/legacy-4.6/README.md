# Legacy DataCite 4.6 JSON Schema profiles (not maintained)

These files are the earlier JSON Schema profiles for DataCite Metadata Schema 4.6. They are kept for reference only and are **not maintained**:

- They predate DataCite 4.7 and lack its `relationTypeInformation` property.
- They do not accept current DataCite REST API records or the output of `validation-and-conversion/scripts/convert.py`.
- Several contain broken references and embed a JSON-LD context that differs from the published one.

Use [`../datacite.schema.json`](../datacite.schema.json) to validate DataCite records, and the published context `https://w3id.org/tib/datacite/context/fullcontext.jsonld` for linked data.
