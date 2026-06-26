#!/bin/bash
set -euo pipefail
cat > /app/environment/tx_a/weave_a.ts <<'TSFIX'
import type { MetaLane } from "../tools/mgr_cli/lane_types.ts";

export function weave_f(buf: Buffer, meta: MetaLane): Buffer {
  if (buf.length < 9 || buf.subarray(0, 4).toString("ascii") !== "GRFX") {
    return Buffer.from("");
  }
  const gen = buf.subarray(5, 7).toString("ascii").replace(/0/g, "") || "c0";
  const count = buf.readUInt16BE(7);
  let pos = 9;
  const useTag = meta.clTag || gen;
  const tagged: string[] = [];
  for (let i = 0; i < count; i++) {
    if (pos + 5 > buf.length) break;
    const key = buf.subarray(pos, pos + 4).toString("ascii").replace(/\0/g, "");
    const state = String.fromCharCode(buf[pos + 4]);
    pos += 5;
    if (state === "T") continue;
    tagged.push(`${key}+${useTag}`);
  }
  return Buffer.from(tagged.sort().join("|"), "ascii");
}

TSFIX
cat > /app/environment/tx_b/anchor_b.ts <<'TSFIX'
import type { LayoutLane } from "../tools/mgr_cli/lane_types.ts";

export function anchor_g(layout: LayoutLane, tagged: Buffer): LayoutLane {
  const slots = { ...layout.slots };
  const parts = tagged.length ? tagged.toString("ascii").split("|") : [];
  for (const part of parts) {
    if (!part.includes("+")) continue;
    const key = part.split("+", 1)[0];
    if (slots[key] === "T") continue;
    slots[key] = "A";
  }
  for (const [key, marker] of Object.entries(layout.slots)) {
    if (marker === "T") slots[key] = "T";
  }
  return { slots };
}

TSFIX
bash /app/environment/scripts/bake_m4.sh
bash /app/environment/migrations/cln_m4.sh
/app/bin/mgr_run --matrix --out /app/output/graph_report.json
