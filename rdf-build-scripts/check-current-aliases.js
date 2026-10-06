#!/usr/bin/env node

// The unversioned dist/datacite.{jsonld,ttl,rdf} files are copies of the
// current version's files, written by update-current-pointers.js. Rebuilding a
// version without re-running that script leaves them stale, so check that each
// alias is byte-identical to dist/datacite-<currentVersion>.<ext>.

const fs = require("fs");
const path = require("path");

const projectRoot = process.cwd();
const roots = ["rdf-vocabulary-staging", "production-namespace"];
const extensions = ["jsonld", "ttl", "rdf"];
const issues = [];

for (const root of roots) {
  const pointer = path.join(projectRoot, root, "manifest", "datacite-current.json");
  if (!fs.existsSync(pointer)) {
    issues.push(`${root}: missing manifest/datacite-current.json`);
    continue;
  }
  const version = JSON.parse(fs.readFileSync(pointer, "utf8")).currentVersion;
  for (const ext of extensions) {
    const alias = path.join(root, "dist", `datacite.${ext}`);
    const source = path.join(root, "dist", `datacite-${version}.${ext}`);
    if (!fs.existsSync(path.join(projectRoot, source))) {
      issues.push(`${source} is missing`);
    } else if (!fs.existsSync(path.join(projectRoot, alias))) {
      issues.push(`${alias} is missing`);
    } else if (!fs.readFileSync(path.join(projectRoot, alias)).equals(fs.readFileSync(path.join(projectRoot, source)))) {
      issues.push(`${alias} differs from ${source}`);
    }
  }
}

if (issues.length) {
  for (const issue of issues) console.error(`- ${issue}`);
  console.error("Run node rdf-build-scripts/update-current-pointers.js, then npm run build:production-namespace.");
  process.exit(1);
}
console.log("Unversioned dist files match the current version.");
