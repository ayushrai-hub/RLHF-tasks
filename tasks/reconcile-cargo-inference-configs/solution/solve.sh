#!/bin/bash
set -euo pipefail

cd /app
mkdir -p src

# Write the TypeScript reconciler. It parses the MLflow export and the two crate
# TOML files, extracts the authoritative run_id from the dossier on stdin, and
# applies the Consolidated Normative Decisions from the dossier to produce the
# canonical release plan under the exact output contract.
cat > src/reconcile.ts <<'TS'
import * as fs from "fs";
import * as crypto from "crypto";
import * as yaml from "js-yaml";
import { parse as parseToml } from "@iarna/toml";

// Full dossier arrives on stdin; the authoritative run_id lives in Appendix R.
function readStdin(): string {
  return fs.readFileSync(0, "utf8");
}

function authoritativeRunId(dossier: string): string {
  const m = dossier.match(/^run_id:\s*([0-9a-f]{8})\s*$/m);
  if (!m) {
    throw new Error("authoritative run_id not found in dossier manifest");
  }
  return m[1];
}

// Minimal RFC-4180 CSV parser: double-quoted fields may contain commas.
function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let inQuotes = false;
  let i = 0;
  while (i < text.length) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 2;
          continue;
        }
        inQuotes = false;
        i += 1;
        continue;
      }
      field += c;
      i += 1;
      continue;
    }
    if (c === '"') {
      inQuotes = true;
      i += 1;
    } else if (c === ",") {
      row.push(field);
      field = "";
      i += 1;
    } else if (c === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
      i += 1;
    } else if (c === "\r") {
      i += 1;
    } else {
      field += c;
      i += 1;
    }
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

function isNumeric(s: string): boolean {
  return s.trim() !== "" && Number.isFinite(Number(s));
}

const dossier = readStdin();
const runId = authoritativeRunId(dossier);

const mlflow: any = yaml.load(
  fs.readFileSync("/app/sources/mlflow-export.yaml", "utf8")
);
const cargo: any = parseToml(fs.readFileSync("/app/crate/Cargo.toml", "utf8"));
const serving: any = parseToml(
  fs.readFileSync("/app/crate/serving.toml", "utf8")
);

// --- Model identity ---------------------------------------------------------
// Name comes from the tracker, never the crate package name.
const name: string = mlflow.model.name;
// Version: MLflow major.minor + crate patch (the 4.3.x crate line was yanked).
const mlParts = String(mlflow.model.version).split(".");
const cratePatch = String(cargo.package.version).split(".")[2];
const version = `${mlParts[0]}.${mlParts[1]}.${cratePatch}`;

// --- Quantization -----------------------------------------------------------
// CPU serving path is certified for int8; serving.toml bf16 is a GPU leftover.
const quantization = "int8";

// --- Serving limits (needed before features) --------------------------------
// Baseline (2026-05-18): batch = min(export 32, crate 16) = 16; concurrency =
// crate value 16; timeout = min(export, crate) = 1500. Later dated revisions
// supersede these (latest date wins):
//   2026-06-12 memory ceiling: resolved batch size reduced to 12
//   2026-06-12 load rehearsal:  resolved concurrency lowered to 12
//   2026-06-12 request budget:  timeout set to 1300, then
//   2026-06-20 re-revision:     timeout set to 1200 (this later date ships)
const maxBatch = 12;
const maxConcurrency = 12;
const requestTimeout = 1200;
// queue_capacity is derived from the resolved batch and concurrency.
const queueCapacity = maxBatch * maxConcurrency;

// --- Feature set ------------------------------------------------------------
function isPowerOfTwo(n: number): boolean {
  return n > 0 && (n & (n - 1)) === 0;
}
const feats = new Set<string>(cargo.features.default as string[]);
feats.delete("telemetry"); // production policy P-114
feats.delete("gpu-cuda"); // never on the CPU path
feats.delete("quantized-bf16"); // must match resolved quantization
feats.add("quantized-int8");
if (maxConcurrency < 16) {
  feats.delete("dynamic-batching");
}
// experimental-simd added iff resolved max batch size is an exact power of two
if (isPowerOfTwo(maxBatch)) {
  feats.add("experimental-simd");
} else {
  feats.delete("experimental-simd");
}
const features = Array.from(feats).sort();

// --- Evaluation metrics from the messy metrics-history.csv ------------------
// Well-formed rows: exactly 5 RFC-4180 fields, non-empty run_id, numeric
// accuracy and latency. Among rows for the authoritative run, pick the latest by
// UTC instant (not by local wall-clock text). Derive gate, ceiling, evaluated_at.
const csvRows = parseCsv(
  fs.readFileSync("/app/sources/metrics-history.csv", "utf8")
);
const dataRows = csvRows.slice(1); // drop header
const wellFormed = dataRows.filter(
  (r) =>
    r.length === 5 &&
    r[0].trim() !== "" &&
    isNumeric(r[2]) &&
    isNumeric(r[3])
);
const runRows = wellFormed.filter((r) => r[0] === runId);
let selected: string[] | null = null;
let bestInstant = -Infinity;
for (const r of runRows) {
  const t = new Date(r[1]).getTime();
  if (t > bestInstant) {
    bestInstant = t;
    selected = r;
  }
}
if (!selected) {
  throw new Error("no well-formed metrics row for the authoritative run");
}
const minAccuracy = Number(selected[2]);
const maxLatency = Math.ceil(Number(selected[3]) * 1.2);
const evaluatedAt = new Date(selected[1]).toISOString().replace(/\.\d{3}Z$/, "Z");

// --- Emit under the exact output contract -----------------------------------
const lines: string[] = [];
lines.push("apiVersion: release.mlops/v1");
lines.push("kind: ReleasePlan");
lines.push("model:");
lines.push(`  name: ${name}`);
lines.push(`  version: ${version}`);
lines.push(`  run_id: ${runId}`);
lines.push(`  evaluated_at: "${evaluatedAt}"`);
lines.push(`quantization: ${quantization}`);
lines.push("features:");
for (const f of features) {
  lines.push(`  - ${f}`);
}
lines.push("thresholds:");
lines.push(`  min_accuracy: ${minAccuracy.toFixed(3)}`);
lines.push(`  max_latency_ms: ${maxLatency}`);
lines.push("serving:");
lines.push(`  max_batch_size: ${maxBatch}`);
lines.push(`  max_concurrency: ${maxConcurrency}`);
lines.push(`  request_timeout_ms: ${requestTimeout}`);
lines.push(`  queue_capacity: ${queueCapacity}`);

const out = lines.join("\n") + "\n";
fs.writeFileSync("/app/release-plan.yaml", out);

// --- Derived deployment descriptor (must stay consistent with the plan) ------
// The following three are resolved from latest-dated narrative decisions whose
// correct (later-dated) value is printed EARLIER than the older decoy:
//   warmup passes:  2026-06-14 -> 8   (decoy 2026-06-01 -> 16)
//   shutdown grace: 2026-06-19 -> 25  (decoy 2026-06-04 -> 40)
//   canary share:   2026-06-16 -> 15  (decoy 2026-06-02 -> 30)
const warmupBatches = 8;
const shutdownGraceSeconds = 25;
const canaryPercent = 15;
const replicas = Math.ceil(maxConcurrency / 4);
const deploy = {
  replicas,
  cpu_millicores: 250 * maxBatch,
  memory_mb: 8 * queueCapacity,
  request_deadline_ms: requestTimeout,
  warmup_batches: warmupBatches,
  shutdown_grace_seconds: shutdownGraceSeconds,
  canary_percent: canaryPercent,
  env: {
    QUANT_MODE: quantization,
    FEATURES: features.join(","),
    MAX_INFLIGHT: String(maxConcurrency),
  },
};
const deployStr = JSON.stringify(deploy, null, 2) + "\n";
fs.writeFileSync("/app/deploy.json", deployStr);

// --- Lockfile binding the two artifacts by SHA-256 ---------------------------
const planSha = crypto.createHash("sha256").update(out, "utf8").digest("hex");
const deploySha = crypto
  .createHash("sha256")
  .update(deployStr, "utf8")
  .digest("hex");
const binding = crypto
  .createHash("sha256")
  .update(`${planSha}:${deploySha}`, "utf8")
  .digest("hex");
const lock = {
  run_id: runId,
  feature_count: features.length,
  replica_count: replicas,
  plan_sha256: planSha,
  deploy_sha256: deploySha,
  binding,
};
fs.writeFileSync("/app/lock.json", JSON.stringify(lock, null, 2) + "\n");

process.stdout.write(out);
TS

# Compile and run the pipeline with the dossier piped on stdin.
tsc -p tsconfig.json
node /app/dist/reconcile.js < /app/dossier.md
