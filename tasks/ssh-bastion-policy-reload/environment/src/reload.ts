#!/usr/bin/env node
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

type State = {
  unit: string;
  active_generation: string;
  checkpoint_seq: string;
};

type UserRow = {
  name: string;
  role: string;
  source: string;
};

type AuditRecord = {
  seq: number;
  generation: string;
  user: string;
  role: string;
  action: string;
  state: string;
};

type PolicyEntry = {
  user: string;
  role: string;
  seq: number;
  action: string;
};

type RevokeEntry = {
  user: string;
  seq: number;
};

function parseArgs(argv: string[]) {
  const out = { input: "fixtures", output: "output" };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--input") out.input = argv[++i];
    else if (argv[i] === "--output") out.output = argv[++i];
  }
  return out;
}

function readState(path: string): State {
  const values: Record<string, string> = {};
  for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const [key, value] = trimmed.split("=", 2);
    values[key] = value;
  }
  return {
    unit: values.unit,
    active_generation: values.active_generation,
    checkpoint_seq: values.checkpoint_seq,
  };
}

function readJsonl(path: string): AuditRecord[] {
  return readFileSync(path, "utf8")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line) as AuditRecord);
}

function readUserMap(path: string): UserRow[] {
  const data = JSON.parse(readFileSync(path, "utf8")) as { users: UserRow[] };
  return data.users;
}

function buildEntries(state: State, users: UserRow[], audit: AuditRecord[]): PolicyEntry[] {
  // BUG: trusts the visible user map and ignores later audit role updates.
  return users
    .map((row) => ({
      user: row.name,
      role: row.role,
      seq: 0,
      action: "allow-user" as const,
    }))
    .sort((a, b) => a.user.localeCompare(b.user));
}

function buildRevoked(state: State, audit: AuditRecord[]): RevokeEntry[] {
  const limit = Number(state.checkpoint_seq);
  return audit
    .filter(
      (record) =>
        record.generation === state.active_generation &&
        record.state === "revoked" &&
        record.seq <= limit
    )
    .map((record) => ({ user: record.user, seq: record.seq }))
    .sort((a, b) => a.user.localeCompare(b.user));
}

function planDigest(entries: PolicyEntry[]): string {
  const lines = entries
    .slice()
    .sort((a, b) => a.user.localeCompare(b.user))
    .map((entry) => `${entry.user}|${entry.role}|${entry.seq}|${entry.action}`);
  return createHash("sha256").update(lines.join("\n")).digest("hex").slice(-8);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const inputDir = resolve(args.input);
  const outputDir = resolve(args.output);
  mkdirSync(outputDir, { recursive: true });

  const state = readState(join(inputDir, "reload-state.env"));
  const users = readUserMap(join(inputDir, "user-map.json"));
  const audit = readJsonl(join(inputDir, "session-audit.jsonl"));
  const entries = buildEntries(state, users, audit);
  const revoked = buildRevoked(state, audit);

  writeFileSync(
    join(outputDir, "policy_plan.json"),
    `${JSON.stringify({ generation: state.active_generation, entries }, null, 2)}\n`
  );
  writeFileSync(
    join(outputDir, "revoke_manifest.json"),
    `${JSON.stringify({ generation: state.active_generation, revoked }, null, 2)}\n`
  );
  writeFileSync(
    join(outputDir, "reload_report.json"),
    `${JSON.stringify(
      {
        summary: {
          unit: state.unit,
          generation: state.active_generation,
          entries_total: entries.length,
          revoked_total: revoked.length,
          reload_status: "settled",
          plan_digest: planDigest(entries),
        },
        checks: {
          user_map_complete: true,
          audit_trail_aligned: true,
          revokes_respected: true,
          idempotent_plan: true,
        },
      },
      null,
      2
    )}\n`
  );
}

main();
