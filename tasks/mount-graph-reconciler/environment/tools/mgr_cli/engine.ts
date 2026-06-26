import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync, existsSync, unlinkSync } from "node:fs";
import { join, dirname } from "node:path";
import * as stageA from "./stage_a.ts";
import * as stageB from "./stage_b.ts";
import * as stageC from "./stage_c.ts";
import { SCENARIOS } from "./scenarios.ts";
import type { AuthPick, LayoutLane, MetaLane, RunCols } from "./lane_types.ts";

const ENV_ROOT = "/app/environment";
const FIX_ROOT = join(ENV_ROOT, "fixtures");
const STAGE = "/app/output/.mgr_stage";
const STAGE_FILE = join(STAGE, "pass_counter");
const CLEAN_MARK = join(STAGE, "clean_mark");

function loadTab(): LayoutLane {
  const raw = readFileSync(join(FIX_ROOT, "tab_frag", "fs0.tab"));
  const slots: Record<string, string> = {};
  if (raw.subarray(0, 4).toString("ascii") === "LAYS" && raw.length >= 7) {
    const count = raw.readUInt16BE(5);
    let pos = 7;
    for (let i = 0; i < count; i++) {
      const key = raw.subarray(pos, pos + 4).toString("ascii").replace(/\0/g, "");
      const marker = String.fromCharCode(raw[pos + 4]);
      slots[key] = marker;
      pos += 5;
    }
  }
  return { slots };
}

function stubHex(): string {
  const stub = JSON.parse(readFileSync(join(FIX_ROOT, "stage_stub", "m3_stub.json"), "utf8"));
  return createHash("sha256").update(JSON.stringify(stub), "ascii").digest("hex");
}

function passNum(): number {
  if (!existsSync(STAGE_FILE)) return 1;
  const n = parseInt(readFileSync(STAGE_FILE, "utf8").trim(), 10);
  return Number.isFinite(n) && n >= 1 ? n : 1;
}

function bumpPass(): void {
  mkdirSync(STAGE, { recursive: true });
  writeFileSync(STAGE_FILE, String(passNum() + 1), "utf8");
  if (existsSync(CLEAN_MARK)) unlinkSync(CLEAN_MARK);
}

function runArm(spec: (typeof SCENARIOS)[number]) {
  const buf = readFileSync(join(FIX_ROOT, "edge_slice", spec.grf));
  const meta: MetaLane = { clTag: spec.cl_tag, sliceName: spec.grf, stubHex: stubHex() };
  const tagged = stageA.run(buf, meta);
  const layout = stageB.run(loadTab(), tagged);
  let pn = passNum();
  if (spec.repeat) pn += 1;
  const cols: RunCols = {
    armId: spec.arm_id,
    clTag: spec.cl_tag,
    passNum: pn,
    stubHex: stubHex(),
  };
  const row = stageC.run(layout, cols, { mode: "slice" } as AuthPick);
  return {
    arm_id: row.armId,
    cl_tag: row.clTag,
    row_digest: row.rowDigest,
    node_tags: row.nodeTags,
    path_a_hex: row.pathAHex,
    path_b_hex: row.pathBHex,
    cross_link: row.crossLink,
  };
}

export function runFullMatrix(outPath: string): Record<string, unknown> {
  if (passNum() > 1 && !existsSync(CLEAN_MARK)) {
    throw new Error("repeat pass without cleanup");
  }
  const arms = SCENARIOS.map(runArm);
  const runToken = createHash("sha256")
    .update(arms.map((a) => a.row_digest).join("|"), "ascii")
    .digest("hex");
  const doc = { schema_ver: "m4", arms, run_token: runToken };
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, JSON.stringify(doc, null, 2) + "\n", "utf8");
  bumpPass();
  return doc;
}
