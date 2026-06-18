#!/usr/bin/env bash
# Generates a production-namespace/ copy of rdf-vocabulary-staging/ for the
# public TIB/w3id namespace.
#
# Usage (from repo root):
#   bash rdf-build-scripts/generate-production-namespace.sh
#
# Defaults:
#   Source namespace:    https://schema.stage.datacite.org/linked-data/
#   Canonical namespace: https://w3id.org/tib/datacite/
#   GitHub Pages path:   /datacite
#   Output directory:    production-namespace/
#
# Override any value with environment variables:
#   SOURCE_NAMESPACE="https://example.test/staging/" \
#   CANONICAL_NAMESPACE="https://w3id.org/tib/datacite/" \
#   PAGES_BASE_PATH="/datacite" \
#   DST="production-namespace" \
#   bash rdf-build-scripts/generate-production-namespace.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SRC="${SRC:-rdf-vocabulary-staging}"
DST="${DST:-production-namespace}"
SOURCE_NAMESPACE="${SOURCE_NAMESPACE:-https://schema.stage.datacite.org/linked-data/}"
CANONICAL_NAMESPACE="${CANONICAL_NAMESPACE:-https://w3id.org/tib/datacite/}"
PAGES_BASE_PATH="${PAGES_BASE_PATH:-/datacite}"

if [ ! -d "$SRC" ]; then
  echo "Error: $SRC not found. Run from the repo root." >&2
  exit 1
fi

rm -rf "$DST"
cp -r "$SRC" "$DST"

export SOURCE_NAMESPACE
export CANONICAL_NAMESPACE
export PAGES_BASE_PATH

find "$DST" -type f | while read -r file; do
  perl -0pi -e 's/\Q$ENV{SOURCE_NAMESPACE}\E/$ENV{CANONICAL_NAMESPACE}/g' "$file"
done

find "$DST" -type f -name "*.html" | while read -r file; do
  perl -0pi -e 's|/linked-data|$ENV{PAGES_BASE_PATH}|g' "$file"
done

# Rebuild section index pages inside the publication bundle so navigation and
# labels match the target GitHub Pages project path.
(
  cd "$DST"
  PAGES_BASE_PATH="$PAGES_BASE_PATH" node "$SCRIPT_DIR/generate-index-pages.js"
)

echo "Done. Production namespace written to $DST/"
echo "Files: $(find "$DST" -type f | wc -l | tr -d ' ')"
echo "Canonical namespace: $CANONICAL_NAMESPACE"
echo "GitHub Pages base path: $PAGES_BASE_PATH"
