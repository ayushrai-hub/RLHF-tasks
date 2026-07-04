const fs = require("fs");
const path = require("path");

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i];
    const value = argv[i + 1];
    if (!key || !key.startsWith("--")) {
      throw new Error(`bad argument near ${key || "<empty>"}`);
    }
    out[key.slice(2)] = value;
  }
  return out;
}

function readIds(filePath) {
  return fs.readFileSync(filePath, "utf8")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function readRun(dirPath, id) {
  const fullPath = path.join(dirPath, `${id}.switchlog`);
  const lines = fs.readFileSync(fullPath, "utf8").trim().split(/\r?\n/);
  const header = lines.shift().split(",");
  return lines.map((line, idx) => {
    const cells = line.split(",");
    const row = {};
    for (let i = 0; i < header.length; i += 1) {
      row[header[i]] = cells[i] || "";
    }
    row.run = id;
    row.idx = idx;
    row.ts = Number.parseInt(row.ts, 10);
    row.ball = Number.parseInt(row.ball, 10);
    return row;
  });
}

module.exports = { parseArgs, readIds, readRun };
