import { weave_f } from "../../tx_a/weave_a.ts";
import type { MetaLane } from "./lane_types.ts";

export function run(buf: Buffer, meta: MetaLane): Buffer {
  return weave_f(buf, meta);
}
