import { anchor_g } from "../../tx_b/anchor_b.ts";
import type { LayoutLane } from "./lane_types.ts";

export function run(layout: LayoutLane, tagged: Buffer): LayoutLane {
  return anchor_g(layout, tagged);
}
