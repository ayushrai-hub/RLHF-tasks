export function decoyWeave(buf: Buffer): string {
  return buf.toString("hex").slice(0, 8);
}
