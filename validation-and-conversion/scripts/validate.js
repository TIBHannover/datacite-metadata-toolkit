// Validate JSON, a collection envelope, or NDJSON. Unknown and empty inputs fail.
const fs = require("fs");
const { validate } = require("jskos-validate");

function readItems(text) {
  if (!text.trim()) throw new Error("Input is empty");
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (_) {
    return text.split(/\r?\n/).filter(line => line.trim()).map(line => JSON.parse(line));
  }
  if (Array.isArray(parsed)) return parsed;
  if (!parsed || typeof parsed !== "object") throw new Error("Expected an object or array");
  const collections = ["mappings", "concepts", "schemes"].filter(key => key in parsed);
  if (!collections.length) return [parsed];
  return collections.flatMap(key => {
    if (!Array.isArray(parsed[key])) throw new Error(`${key} must be an array`);
    return parsed[key];
  });
}

function validatorFor(item) {
  if (!item || typeof item !== "object" || Array.isArray(item)) return null;
  const rawType = item.type || item["@type"] || [];
  const types = Array.isArray(rawType) ? rawType : [rawType];
  if ("from" in item || "to" in item || types.some(type =>
    typeof type === "string" && /^http:\/\/www\.w3\.org\/2004\/02\/skos\/core#(exact|close|broad|narrow|related)Match$/.test(type))) {
    return validate.mapping;
  }
  if (types.some(type => ["skos:ConceptScheme", "http://www.w3.org/2004/02/skos/core#ConceptScheme"].includes(type))) return validate.scheme;
  if (types.some(type => ["skos:Concept", "http://www.w3.org/2004/02/skos/core#Concept"].includes(type))) return validate.concept;
  return null;
}

try {
  const path = process.argv[2] || "mappings/jskos-mappings.json";
  const items = readItems(fs.readFileSync(path, "utf8"));
  if (!items.length) throw new Error("Input contains no items");
  let valid = 0;
  let invalid = 0;
  let unknown = 0;
  for (const [index, item] of items.entries()) {
    const check = validatorFor(item);
    if (!check) {
      unknown++;
      console.error(`Item ${index}: unknown JSKOS item type`);
    } else if (check(item)) {
      valid++;
    } else {
      invalid++;
      console.error(`Item ${index}: INVALID`);
      for (const error of check.errorMessages || []) console.error("  -", error);
    }
  }
  console.log(`Summary: ${valid} valid, ${invalid} invalid, ${unknown} unknown (of ${items.length} total).`);
  if (invalid || unknown || !valid) process.exitCode = 1;
} catch (error) {
  console.error(`Validation failed: ${error.message}`);
  process.exitCode = 1;
}
