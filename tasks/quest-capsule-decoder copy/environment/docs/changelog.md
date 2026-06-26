# Loader changelog

## Loader changelog (inherited, lightly annotated)

- **QC1 -> QC2.** QC1 stored the header as plain `key=value` text with no base64 and no
  glyph encoding; numbers were ordinary digits. QC2 wrapped the record in base64 and moved
  every number except `g` into glyphs. All shipped capsules are QC2; I keep this note only
  so nobody wastes time looking for a QC1 capsule that no longer exists.
- **Check field added.** Early QC2 capsules had no `k`. The `(e + n + s) mod 9973` check
  was added after a batch of corrupted seeds shipped; a missing `k` is a pre-check capsule
  and should be treated as "check not present" rather than "check failed".
- **Glyph sets split per capsule.** Originally one global glyph set; now each capsule names
  its set in `g`. Set 7 is the one in the current cartridge. Always decode with the set the
  header names, never with whatever set you decoded the last capsule with.
- **Seed semantics clarified.** A support ticket insisted the seed was an RNG seed. It is
  not. It is a rotation offset into the sorted exit list. Same seed, same walk, every time.

