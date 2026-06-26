import { settle_h } from "../../tx_c/settle_c.ts";
import type { AuthPick, LayoutLane, ReportRow, RunCols } from "./lane_types.ts";

export function run(layout: LayoutLane, cols: RunCols, pick: AuthPick): ReportRow {
  return settle_h(layout, cols, pick);
}
