# HLS recovery configuration + segment decryption

## Manifest layout

`HLS_INPUT/manifests/<playlist_id>.m3u8` is a standard HLS playlist
with one `#EXT-X-KEY:METHOD=AES-128,URI="key://<playlist_id>/<key_version>",IV=0x<hex>`
line followed by a sequence of `#EXTINF:` + segment file lines.
Segments live at `HLS_INPUT/segments/<index>.ts.enc` and are encrypted
with AES-128 CBC PKCS#7 using the playlist's IV and the unwrapped
content key.

## `recovery_config.json` - the broken file

`/app/data/recovery_config.json` ships pre-corrupted with five fields,
all five of which must be repaired by `recover-config`:

| Field                     | Broken value                 | Correct replacement                                   |
|---------------------------|------------------------------|-------------------------------------------------------|
| master_key_path           | `"/etc/keys/master.bin"`     | `MASTER_KEY` env value (default `/opt/evidence_keys/master.key.hex`) |
| key_wrap_algorithm        | `"AES-GCM-256"`              | `"AES-KW-256"`                                        |
| segment_cipher            | `"AES-256-CTR"`              | `"AES-128-CBC"`                                       |
| segment_padding           | `"none"`                     | `"PKCS#7"`                                            |
| audit_log_table           | `"audit"`                    | `"audit_log"`                                         |

`recover-config` overwrites the file with a JSON object containing the
five corrected fields (no extra fields), keys in ASCII-ascending
order, two-space indented, terminated with a newline. The return
value lists the field names that changed, sorted ASCII-ascending.

## `decrypt` flow

1. Open the playlist row by parsing the segment index lookup table
   (`/app/data/segment_index.json`, generated at image build).
2. Verify `wrapped_keys.sig_hex` for the playlist + active key
   version. If it fails, log `decision=deny` to `audit_log` and exit 1
   with `{"error":"sig_mismatch","message":"..."}`.
3. Unwrap `wrapped_key_hex` with AES-KW using the master key. If unwrap
   fails, log `deny` and exit 1 with `{"error":"unwrap_failed",...}`.
4. Read `HLS_INPUT/segments/<index>.ts.enc`, AES-128 CBC decrypt with
   the unwrapped key and the playlist IV, strip PKCS#7, write the
   plaintext to `HLS_INPUT/segments/<index>.ts`.
5. Log `decision=allow` with `action=decrypt`, `target=<index>`.

## `remux <playlist_id>` flow

1. Locate the manifest and the plaintext segment files written by
   prior `decrypt` calls. If any are missing, exit 1 with
   `{"error":"missing_segments",...}`.
2. Build the canonical ffmpeg argv vector (see `validator-rules.md`
   for the allowlist), invoke ffmpeg, and write the MP4 to
   `ARTIFACTS/<playlist_id>.mp4`.
3. SHA-256 the MP4 bytes; insert one row into `artifacts`; log a
   `remux` row in `audit_log` with `decision=allow`.

## Determinism

ffmpeg argv MUST include `-fflags +bitexact` before `-i`, plus
`-flags +bitexact -map_metadata -1 -c copy` after `-i`, so concat-mux
is bit-exact across reruns. Input-only options before `-i`; output
options after. The
`audit_log.ts_epoch_ms` value is sourced from
`RECOVERY_NOW_OVERRIDE` when set (unix ms), otherwise
`System.currentTimeMillis()`.
