import type { LayoutLane } from "../tools/mgr_cli/lane_types.ts";

export function anchor_g(layout: LayoutLane, tagged: Buffer): LayoutLane {
  const slots = { ...layout.slots };
  const parts = tagged.length ? tagged.toString("ascii").split("|") : [];
  for (const part of parts) {
    if (!part.includes("+")) continue;
    const key = part.split("+", 1)[0];
    slots[key] = "A";
  }
  return { slots };
}
