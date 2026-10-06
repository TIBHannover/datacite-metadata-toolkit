#!/usr/bin/env python3
"""Build SKOS/JSKOS from all curated SSSOM sets; --check never writes files."""

import argparse
import sys
from pathlib import Path

from mapping_tools import MappingError, build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if validation fails or generated exports are stale")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        counts, unique, sources = build(args.root, check=args.check)
    except (MappingError, OSError) as error:
        print(f"Mapping check failed: {error}", file=sys.stderr)
        return 1
    print(f"Validated {sources} canonical sources for each target; rows: {counts}; {unique} unique triples in both exports.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
