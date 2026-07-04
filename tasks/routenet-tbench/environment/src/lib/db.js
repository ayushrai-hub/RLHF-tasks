"use strict";

const { Client } = require("pg");
const { readJson } = require("./util");

const DEFAULT_CONFIG_PATH = "/app/config/db.json";

async function connect(configPath = DEFAULT_CONFIG_PATH) {
  const cfg = readJson(configPath);
  const client = new Client({
    host: cfg.host,
    port: cfg.port,
    user: cfg.user,
    password: cfg.password,
    database: cfg.database,
    application_name: cfg.application_name,
  });
  await client.connect();
  return client;
}

async function fetchNodes(client) {
  const res = await client.query("SELECT id, label, kind FROM nodes ORDER BY id");
  return res.rows.map((r) => ({ id: r.id, label: r.label, kind: r.kind }));
}

async function fetchEdges(client, split) {
  if (split === undefined) {
    const res = await client.query("SELECT u, v, split FROM edges");
    return res.rows.map((r) => ({ u: r.u, v: r.v, split: r.split }));
  }
  const res = await client.query(
    "SELECT u, v FROM edges WHERE split = $1",
    [split],
  );
  return res.rows.map((r) => ({ u: r.u, v: r.v }));
}

async function fetchNodeIds(client) {
  const res = await client.query("SELECT id FROM nodes ORDER BY id");
  return res.rows.map((r) => r.id);
}

async function disconnect(client) {
  if (client) await client.end();
}

module.exports = {
  connect,
  disconnect,
  fetchNodes,
  fetchEdges,
  fetchNodeIds,
};
