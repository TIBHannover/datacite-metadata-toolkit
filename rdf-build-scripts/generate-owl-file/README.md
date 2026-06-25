# Script for generating OWL file from vocab, class and property JSON-LD files

## Overview

The script collects the JSON-LD files from the vocab, class, and property directories in the rdf-vocabulary-staging directory. It parses them into one RDF graph, adds the required ontology metadata and writes the graph to an OWL file.


### Input

- Source: https://github.com/selgebali/datacite-metadata-toolkit/tree/main/rdf-vocabulary-staging


### Output

The output of this script will be generated in the `rdf-vocabulary-staging/dist` directory. This folder is where all distribution files live.

- Filename: `datacite-<version>.owl`, for example `datacite-4.7.owl`


## Setup

To execute the script run the following commands. Make sure to set the working directory to this scripts folder 
(current path: `rdf-build-scripts/generate-owl-file`.

### create or start virtual environment

```
# If not created, create virtualenv
python3 -m venv venv 
# Activate virtualenv
source ./venv/bin/activate
# Update pip
pip install --upgrade pip
# Install dependencies
pip install -r ./requirements.txt 
```
### set environment variables

```
# set version (replace <version> for example with 4.7)
DATACITE_VERSION="<version>"

# set namespace (replace <namespace> for example with https://w3id.org/tib/datacite/)
DATACITE_NAMESPACE="<namespace>"

# optional: set ontology created date; defaults to releaseDate in the version manifest
DATACITE_CREATED_DATE="YYYY-MM-DD"
```

`DATACITE_CREATED_DATE` must use `YYYY-MM-DD`. If it is not set, the script reads `releaseDate` from `rdf-vocabulary-staging/manifest/datacite-<version>.json`. This keeps regenerated OWL output stable instead of changing every day.

### run script

```
python generate-owl-file.py
```
