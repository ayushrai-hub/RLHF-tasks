# Six validator rules - HLS spec edge cases

`validate <rule> [<playlist_id>]` accepts exactly one of the six rule
names below plus an optional playlist id (default `cam001`). Each rule
is a boolean check against the manifests, segment files, and
`wrapped_keys` rows currently visible to the process. The manifest root
is read from the `HLS_MANIFESTS_DIR` environment variable (default
`/app/data/hls_export/manifests/`) and the segment root from
`HLS_SEGMENTS_DIR` (default `/app/data/hls_export/segments/`). Both
overrides must be honoured so the verifier can point the validator at
per-case scratch trees under `/tmp` without mutating the canonical
input set. The rule outcome (`true`/`false`) is folded into the named
playlist's `audit_validator_sha256` (see `audit-chain.md`). The
fixtures provide two valid and two invalid cases per rule; the
verifier exercises all 24 to confirm correctness.

## 1. `byte_range_parse`

Every `#EXT-X-BYTERANGE:` directive in every manifest decodes to a
`length@offset` pair where both `length` and `offset` are
non-negative base-10 integers and `length > 0`. Manifests without any
byte-range directive pass trivially. Hex, signed, or
whitespace-padded values are invalid.

## 2. `key_uri_format`

Every `#EXT-X-KEY:` URI matches the regex
`^key://[a-z0-9_-]{1,32}/[1-9][0-9]{0,3}$` exactly. The first segment
is the playlist id, the second is the key version. Multiple key lines
in the same manifest must all share the playlist id; the key version
must strictly increase.

## 3. `iv_pinning`

Every `#EXT-X-KEY:` IV attribute is `0x` followed by exactly 32 lowercase
hex characters. The IV bytes equal the `iv_hex` value stored in
`wrapped_keys` for the same (`playlist_id`, `key_version`). Manifests
where the in-band IV disagrees with the table fail.

## 4. `ext_x_key_scope`

`#EXT-X-KEY:` lines appear before any `#EXTINF:` line they cover and
remain in effect until either the next `#EXT-X-KEY:` line or end of
manifest. A manifest that declares `METHOD=AES-128` but contains a
`#EXTINF:` line not preceded by any `#EXT-X-KEY:` fails. A
`METHOD=NONE` line that follows an `AES-128` line is permitted only
when it precedes a different playlist break.

Critically, the rule fails any manifest in which one or more
`#EXTINF:` segments are NOT covered by a currently-active
`METHOD=AES-128` key line. This includes:

* manifests with zero `#EXT-X-KEY:` lines but at least one `#EXTINF:`,
* manifests in which the only `#EXT-X-KEY:` line carries `METHOD=NONE`,
* manifests where a `METHOD=NONE` line is followed by `#EXTINF:`
  segments with no subsequent `METHOD=AES-128` reinstatement.

In other words, every `#EXTINF:` segment in the manifest MUST have a
preceding `#EXT-X-KEY:METHOD=AES-128` in scope; the absence of any
`AES-128` coverage is `valid=false`.

## 5. `segment_encryption_rotation`

A manifest may rotate keys mid-stream by emitting a second
`#EXT-X-KEY:` with a strictly larger `key_version`. Rotation is valid
only when (a) the new key version exists in `wrapped_keys` for the
playlist, (b) at least one segment follows the rotation line, and
(c) the previous key version was used by at least one segment.

## 6. `codec_private_integrity`

The first segment of each playlist embeds a 16-byte codec private
data block (the test fixture concatenates it ahead of the encrypted
payload). The SHA-256 of those 16 bytes MUST equal
`playlists.codec_private_sha256`. Any drift fails the rule.

## Fixture inventory

`/app/fixtures/validator_cases.json` lists the 24 fixtures
(`rule`, `playlist_id`, `expected_valid`). The verifier iterates them
and asserts `validate <rule> <playlist_id>` returns the expected
boolean while pointing `HLS_MANIFESTS_DIR` (and, where applicable,
`HLS_SEGMENTS_DIR`) at the per-case manifests directory under `/tmp`.
Calls whose resolved `HLS_MANIFESTS_DIR` (absolute, normalised) equals
the canonical default `/app/data/hls_export/manifests/` are
"canonical" and MUST fold their outcome into
`playlists.audit_validator_sha256`; calls whose resolved manifests
directory is anything else are "scratch" and MUST NOT mutate the
column (see `audit-chain.md`). The verifier sequences the
canonical-input calls and then checks `audit_validator_sha256`
against `/app/fixtures/expected_validators.json`.
