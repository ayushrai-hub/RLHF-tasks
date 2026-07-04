#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const SAMPLER_PATH = "/app/src/lib/sampler.js";

function parseArgs(argv) {
  const out = {};
  for (const a of argv) {
    if (!a.startsWith("--")) continue;
    const eq = a.indexOf("=");
    if (eq === -1) out[a.slice(2)] = true;
    else out[a.slice(2, eq)] = a.slice(eq + 1);
  }
  return out;
}

function stripComments(src) {
  let out = "";
  let i = 0;
  const n = src.length;
  while (i < n) {
    const c = src[i];
    const c2 = src[i + 1];
    if (c === "/" && c2 === "/") {
      while (i < n && src[i] !== "\n") i++;
    } else if (c === "/" && c2 === "*") {
      i += 2;
      while (i < n && !(src[i] === "*" && src[i + 1] === "/")) i++;
      i += 2;
    } else if (c === '"' || c === "'" || c === "`") {
      const quote = c;
      out += c;
      i++;
      while (i < n) {
        if (src[i] === "\\") {
          out += src[i] + (src[i + 1] || "");
          i += 2;
          continue;
        }
        out += src[i];
        if (src[i] === quote) {
          i++;
          break;
        }
        i++;
      }
    } else {
      out += c;
      i++;
    }
  }
  return out;
}

function collectStringLiterals(src) {
  const lits = [];
  const re = /(['"`])((?:\\.|(?!\1).)*)\1/g;
  let m;
  while ((m = re.exec(src)) !== null) {
    lits.push(m[2]);
  }
  return lits;
}

function auditSource(src) {
  const violations = [];
  const code = stripComments(src);
  const literals = collectStringLiterals(src);

  const snapshotExtRe = /\.(json|csv|tsv|ndjson)\b/i;
  const snapshotPathHits = literals.filter((l) => /\/data\//i.test(l) && snapshotExtRe.test(l));
  if (snapshotPathHits.length > 0) {
    violations.push({
      rule: "no-snapshot-source",
      message: `sampler references on-disk graph snapshot path: ${snapshotPathHits.join(", ")}`,
    });
  }

  const readFileCall = /\bfs\.\s*readFile(Sync)?\s*\(/.test(code) ||
    /\brequire\(\s*['"]fs['"]\s*\)\.\s*readFile(Sync)?\s*\(/.test(code);
  if (readFileCall) {
    const readsData = literals.some((l) => /\/app\/data\//.test(l) || /^data\//.test(l));
    if (readsData) {
      violations.push({
        rule: "no-fs-readfile-of-data",
        message: "sampler reads files under /app/data/ via fs.readFile*",
      });
    }
  }

  const usesPg = /\brequire\(\s*['"]pg['"]\s*\)/.test(code) ||
    /\bfrom\s+['"]pg['"]/.test(code) ||
    /\brequire\(\s*['"]\.\.\/lib\/db['"]\s*\)/.test(code) ||
    /\brequire\(\s*['"]\.\/db['"]\s*\)/.test(code) ||
    /\brequire\(\s*['"][^'"]*\/db['"]\s*\)/.test(code);
  if (!usesPg) {
    violations.push({
      rule: "requires-pg",
      message: "sampler does not require the pg module (or the db helper that wraps it)",
    });
  }

  if (/\bMath\.\s*random\s*\(/.test(code)) {
    violations.push({
      rule: "seeded-randomness",
      message: "sampler uses Math.random; randomness must be driven by a seeded PRNG",
    });
  }

  const pairLiteralRe = /\[\s*\d+\s*,\s*\d+\s*\]/g;
  const pairLiteralCount = (code.match(pairLiteralRe) || []).length;
  if (pairLiteralCount >= 8) {
    violations.push({
      rule: "no-hardcoded-pairs",
      message: `sampler contains ${pairLiteralCount} hard-coded [u, v] pair literals`,
    });
  }

  return violations;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const outputPath = args.output || "/app/output/audit.json";
  const samplerPath = args.source || SAMPLER_PATH;

  let src;
  try {
    src = fs.readFileSync(samplerPath, "utf8");
  } catch (err) {
    const result = {
      status: "fail",
      sampler_path: samplerPath,
      violations: [
        { rule: "source-missing", message: `cannot read ${samplerPath}: ${err.message}` },
      ],
    };
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + "\n");
    process.stdout.write(`audit: fail (${result.violations.length} violations) -> ${outputPath}\n`);
    process.exit(1);
  }

  const violations = auditSource(src);
  const result = {
    status: violations.length === 0 ? "ok" : "fail",
    sampler_path: samplerPath,
    violations,
  };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + "\n");
  process.stdout.write(
    `audit: ${result.status} (${violations.length} violations) -> ${outputPath}\n`,
  );
  process.exit(result.status === "ok" ? 0 : 1);
}

main();
