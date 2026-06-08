# Script for generating OWL file from vocab, class and property JSON-LD files

## Overview

The script collects the JSON-LD files from the vocab, class, and property directories in the rdf-vocabulary-staging directory. It parses them into one RDF graph, adds the required ontology metadata and writes the graph to an OWL file.


### Input

- Source: https://github.com/selgebali/datacite-metadata-toolkit/tree/main/rdf-vocabulary-staging


### Output

The output of this script will be generated in the `out` directory within this scripts directory.

- Filename: `datacite.owl`


## Setup

To execute the script run the following commands. Make sure to set the working directory to this scripts folder.

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

### Run script

```
python generate-owl-file.py
```