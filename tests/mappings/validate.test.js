// Exit-status tests for validation-and-conversion/scripts/validate.js.
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const root = path.resolve(__dirname, "../..");
const script = path.join(root, "validation-and-conversion/scripts/validate.js");

function run(content) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "jskos-"));
  const file = path.join(dir, "input.json");
  fs.writeFileSync(file, content);
  try {
    return spawnSync(process.execPath, [script, file], { encoding: "utf8" });
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

const valid = {
  from: { memberSet: [{ uri: "https://w3id.org/tib/datacite/property/title" }] },
  to: { memberSet: [{ uri: "http://purl.org/dc/terms/title" }] },
  type: ["http://www.w3.org/2004/02/skos/core#closeMatch"],
};

test("repository JSKOS export is valid", () => {
  const result = spawnSync(process.execPath, [script, path.join(root, "mappings/jskos-mappings.json")], { encoding: "utf8" });
  assert.strictEqual(result.status, 0, result.stderr);
});

test("valid mapping passes", () => {
  assert.strictEqual(run(JSON.stringify({ mappings: [valid] })).status, 0);
});

test("invalid concept bundle fails", () => {
  const invalid = { ...valid, from: { uri: valid.from.memberSet[0].uri } };
  assert.notStrictEqual(run(JSON.stringify({ mappings: [invalid] })).status, 0);
});

test("empty and unknown inputs fail", () => {
  assert.notStrictEqual(run("").status, 0);
  assert.notStrictEqual(run(JSON.stringify({ mappings: [] })).status, 0);
  assert.notStrictEqual(run(JSON.stringify({ foo: "bar" })).status, 0);
});
