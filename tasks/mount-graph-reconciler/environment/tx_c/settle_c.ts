import { createHash } from "node:crypto";
import type { AuthPick, LayoutLane, ReportRow, RunCols } from "../tools/mgr_cli/lane_types.ts";

export function settle_h(layout: LayoutLane, cols: RunCols, _pick: AuthPick): ReportRow {
  const nodeTags = Object.entries(layout.slots)
    .filter(([, v]) => v === "A")
    .map(([k]) => `${k}+${cols.clTag}`)
    .sort();
  const slotParts = Object.entries(layout.slots)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}:${v}`);
  const pathA = createHash("sha256").update(slotParts.join("|"), "ascii").digest("hex");
  const pathB =
    cols.passNum > 1 && cols.stubHex
      ? cols.stubHex
      : createHash("sha256").update(nodeTags.join(""), "ascii").digest("hex");
  const cross = createHash("sha256")
    .update(`${pathA}|${pathB}|${cols.clTag}`, "ascii")
    .digest("hex");
  const digestSrc = `${cols.clTag}|${nodeTags.join("|")}|${cross}`;
  const rowDigest = createHash("sha256").update(digestSrc, "ascii").digest("hex");
  return {
    armId: cols.armId,
    clTag: cols.clTag,
    rowDigest,
    nodeTags,
    pathAHex: pathA,
    pathBHex: pathB,
    crossLink: cross,
  };
}
