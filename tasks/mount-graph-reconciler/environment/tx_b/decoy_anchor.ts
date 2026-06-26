import type { LayoutLane } from "../tools/mgr_cli/lane_types.ts";

export function decoyAnchor(layout: LayoutLane): LayoutLane {
  return { slots: { ...layout.slots } };
}
