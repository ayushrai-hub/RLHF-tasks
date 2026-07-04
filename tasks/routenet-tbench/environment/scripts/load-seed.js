#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { Client } = require("pg");

const DATA_DIR = "/app/data";
const CONFIG_PATH = "/app/config/db.json";

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const header = lines[0].split(",");
  const out = [];
  for (let i = 1; i < lines.length; i++) {
    const row = lines[i].split(",");
    const obj = {};
    for (let j = 0; j < header.length; j++) {
      obj[header[j]] = row[j];
    }
    out.push(obj);
  }
  return out;
}

async function main() {
  const cfg = JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
  const client = new Client({
    host: cfg.host,
    port: cfg.port,
    user: cfg.user,
    password: cfg.password,
    database: cfg.database,
  });
  await client.connect();

  try {
    await client.query("DROP TABLE IF EXISTS edges");
    await client.query("DROP TABLE IF EXISTS splits");
    await client.query("DROP TABLE IF EXISTS nodes");

    await client.query(`
      CREATE TABLE nodes (
        id    INTEGER PRIMARY KEY,
        label TEXT NOT NULL,
        kind  TEXT NOT NULL
      )
    `);
    await client.query(`
      CREATE TABLE edges (
        u     INTEGER NOT NULL REFERENCES nodes(id),
        v     INTEGER NOT NULL REFERENCES nodes(id),
        split TEXT NOT NULL
      )
    `);
    await client.query(`
      CREATE TABLE splits (
        name  TEXT PRIMARY KEY,
        count INTEGER NOT NULL
      )
    `);

    const nodes = parseCsv(fs.readFileSync(path.join(DATA_DIR, "nodes.csv"), "utf8"));
    for (const n of nodes) {
      await client.query(
        "INSERT INTO nodes (id, label, kind) VALUES ($1, $2, $3)",
        [parseInt(n.id, 10), n.label, n.kind],
      );
    }

    const edges = parseCsv(fs.readFileSync(path.join(DATA_DIR, "edges.csv"), "utf8"));
    const counts = { train: 0, val: 0, test: 0 };
    for (const e of edges) {
      await client.query(
        "INSERT INTO edges (u, v, split) VALUES ($1, $2, $3)",
        [parseInt(e.u, 10), parseInt(e.v, 10), e.split],
      );
      counts[e.split] = (counts[e.split] || 0) + 1;
    }
    for (const [name, count] of Object.entries(counts)) {
      await client.query(
        "INSERT INTO splits (name, count) VALUES ($1, $2)",
        [name, count],
      );
    }

    await client.query("CREATE INDEX edges_split_idx ON edges(split)");
    await client.query("CREATE INDEX edges_u_idx ON edges(u)");
    await client.query("CREATE INDEX edges_v_idx ON edges(v)");

    process.stdout.write(`loaded ${nodes.length} nodes, ${edges.length} edges\n`);
  } finally {
    await client.end();
  }
}

main().catch((err) => {
  process.stderr.write(`load-seed failed: ${err.stack || err.message || err}\n`);
  process.exit(1);
});
