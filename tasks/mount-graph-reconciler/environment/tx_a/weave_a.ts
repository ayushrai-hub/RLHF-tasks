import type { MetaLane } from "../tools/mgr_cli/lane_types.ts";

export function weave_f(buf: Buffer, meta: MetaLane): Buffer {
  if (buf.length < 9 || buf.subarray(0, 4).toString("ascii") !== "GRFX") {
    return Buffer.from("");
  }
  const gen = buf.subarray(5, 7).toString("ascii").replace(/0/g, "") || "c0";
  const count = buf.readUInt16BE(7);
  let pos = 9;
  const tagged: string[] = [];
  for (let i = 0; i < count; i++) {
    if (pos + 5 > buf.length) break;
    const key = buf.subarray(pos, pos + 4).toString("ascii").replace(/\0/g, "");
    pos += 5;
    tagged.push(`${key}+${gen}`);
  }
  if (meta.stubHex && tagged.length < 3) {
    tagged.push(`stub+${meta.stubHex.slice(0, 6)}`);
  }
  return Buffer.from(tagged.join("|"), "ascii");
}
