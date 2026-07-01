#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const projectRoot = process.cwd();
const roots = ["rdf-vocabulary-staging", "production-namespace"];
const versionedTitlePattern = /^DataCite\s+\d+(?:\.\d+)+\b/i;
const issues = [];

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (err) {
    issues.push({
      file,
      message: `invalid JSON (${err.message})`,
    });
    return null;
  }
}

function checkNode(file, graphNode) {
  if (!graphNode) return;

  const type = graphNode.type || graphNode["@type"];
  const types = Array.isArray(type) ? type : [type];
  if (!types.includes("ConceptScheme") && !types.includes("skos:ConceptScheme")) {
    return;
  }

  if (typeof graphNode.title === "string" && versionedTitlePattern.test(graphNode.title)) {
    issues.push({
      file,
      message: `ConceptScheme title must not include a schema version: "${graphNode.title}"`,
    });
  }
}

function checkJsonldFile(file, mode) {
  const json = readJson(file);
  if (!json) return;

  if (mode === "scheme") {
    checkNode(file, Array.isArray(json["@graph"]) ? json["@graph"][0] : json);
    return;
  }

  const nodes = Array.isArray(json["@graph"]) ? json["@graph"] : [json];
  for (const node of nodes) {
    checkNode(file, node);
  }
}

function checkRoot(rootName) {
  const vocabRoot = path.join(projectRoot, rootName, "vocab");
  if (fs.existsSync(vocabRoot)) {
    for (const dirent of fs.readdirSync(vocabRoot, { withFileTypes: true })) {
      if (!dirent.isDirectory()) continue;
      const schemeFile = path.join(vocabRoot, dirent.name, `${dirent.name}.jsonld`);
      if (fs.existsSync(schemeFile)) {
        checkJsonldFile(schemeFile, "scheme");
      }
    }
  }

  const distRoot = path.join(projectRoot, rootName, "dist");
  if (!fs.existsSync(distRoot)) return;

  for (const dirent of fs.readdirSync(distRoot, { withFileTypes: true })) {
    if (!dirent.isFile() || !dirent.name.endsWith(".jsonld")) continue;
    checkJsonldFile(path.join(distRoot, dirent.name), "graph");
  }
}

for (const root of roots) {
  checkRoot(root);
}

if (issues.length) {
  console.error("Versioned vocabulary scheme titles found:");
  for (const issue of issues) {
    console.error(` - ${path.relative(projectRoot, issue.file)}: ${issue.message}`);
  }
  process.exit(1);
}

console.log("Vocabulary scheme titles are version-neutral.");
