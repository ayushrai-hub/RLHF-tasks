# Exhibit Media Signing Policy

The gallery kiosk displays exhibit images only when their provenance can be
established from a detached cryptographic signature. This document defines the
records the audit reads, how a key's current trust state is established, the
conventions that make a signature authentic, and the remediation taxonomy the audit
reports. It describes what each record means, not how to implement the library.

## Stored records

The local SQLite database referenced by the audit contract holds three tables. It is
a **stale snapshot**: its key `status`, `trusted`, `revocation_reason`, and
`revoked_at` columns are only a point-in-time copy and are not authoritative. The
crypto identity and validity window it records are stable and are trusted.

`keys` — one row per signing key.

| column | meaning |
| --- | --- |
| `key_id` | stable identifier of the key |
| `algorithm` | `rsa`, `ec`, or `ed25519` |
| `digest_algorithm` | pre-hash used for `rsa`/`ec` keys; `NULL` for `ed25519` |
| `fingerprint` | the key's recorded SPKI fingerprint |
| `public_key_path` | path to the PEM public key |
| `status`, `trusted`, `revocation_reason`, `revoked_at` | stale trust snapshot (see Reconciliation) |
| `not_before`, `not_after` | bounds of the key's validity window |

`images` — one row per exhibit image: `image_id`, `media_path`, `signature_path`,
`key_id` (the signing key), and `signed_at` (when the image was signed).

`policy_exceptions` — provenance waivers granted to individual images:
`exception_id`, `image_id` (the covered image), `reason`, and `expires_at`. An image
has at most one exception, and many images have none.

All record paths are relative to the application root.

## Trust Registry

The authoritative, current trust state of every key lives in the local Trust Registry
service, reachable at the base URL in the contract. It is the source of truth; the
database columns above are only a stale copy of it.

- `GET /v1/keystates?cursor=<c>` returns one page `{"records": [...], "next_cursor":
  <string or null>}`. Reading begins at the contract's start cursor and continues while
  `next_cursor` is non-null. Records for a single key are spread across pages and are
  not ordered.
- `GET /v1/voids` returns `{"expunged": [{"key_id": ..., "expunged_at": ...}, ...]}`,
  the keys that have been removed from trust.
- `GET /v1/ping` is a health check.

Each key-state record has `key_id`, an integer `revision`, an `as_of` instant, and the
key's `status`, `trusted`, `revocation_reason`, and `revoked_at` as of that revision. A
record whose `as_of` is after `audit_time` is not yet in effect.

## Reconciliation

Each key's current state is reconciled from the registry, falling back to the database:

- Consider only the key's registry records whose `as_of` is at or before `audit_time`.
  Among those effective records, the one with the highest `revision` gives the key's
  current `status`, `trusted`, `revocation_reason`, and `revoked_at`.
- A key named in the void feed is `revoked` with reason `key_expunged` and
  `revoked_at` set to its `expunged_at`, regardless of its records; its trust flag is
  the one from its latest effective record.
- A key with no effective registry record and no void keeps the database's snapshot of
  `status`, `trusted`, `revocation_reason`, and `revoked_at`.

A key's `algorithm`, `digest_algorithm`, `fingerprint`, `public_key_path`, and validity
window always come from the database.

## Instants

Every instant is an ISO-8601 timestamp; some carry a non-UTC zone offset. Every emitted
instant is normalized to UTC in the canonical form `YYYY-MM-DDTHH:MM:SSZ` (whole-second,
Zulu), and instants are compared as the UTC instants they denote, never as raw text. The
contract fixes a single `audit_time`; every judgment about a key's current state is made
against it, not the wall clock.

## Signing catalog

The catalog is the join of every image with its reconciled signing key and its exception
(if any), ordered by `image_id`. Each entry carries the image identifiers and paths, the
key's algorithm, digest algorithm, recorded fingerprint, public-key path, reconciled
status, reconciled trust flag, normalized validity window, reconciled revocation reason
and normalized revocation instant, the normalized `signed_at`, and the exception
identifier and normalized expiry. `key_trusted` is a JSON boolean. The digest algorithm,
the revocation fields, and the exception fields are JSON `null` when absent. `row_count`
is the number of images.

## Signature evidence

For each cataloged image the audit establishes whether its detached signature is
trustworthy.

A key's **SPKI fingerprint** is the lowercase hex SHA-256 digest of the key's DER-encoded
`SubjectPublicKeyInfo`. Before any signature is trusted, the fingerprint computed from the
on-disk public key must equal the fingerprint recorded for the key; a key whose computed
fingerprint does not match has an unconfirmed identity and its signatures are never
trusted.

A detached signature does not cover the media bytes. It covers the image's **content
manifest**: the UTF-8 byte string of four lines, each terminated by a single line feed, in
order — the manifest version tag from the contract, the `image_id`, the token `sha256=`
followed by the lowercase hex SHA-256 of the media file, and the `signed_at` in canonical
UTC. Verification reconstructs the manifest from the catalog and the media on disk.
Detached signature files hold the base64 encoding of the raw signature bytes.

Pre-hash algorithms (`rsa`, `ec`) are verified with a message digest, recorded as method
`dgst`; raw algorithms (`ed25519`) are verified over the whole manifest with no pre-hash,
recorded as method `pkeyutl`. For pre-hash keys the digest is the key's `digest_algorithm`.

A signature is **valid** only when the fingerprint matches and it verifies against the
reconstructed manifest. The evidence for each image records the verification method, the
computed fingerprint, whether it matched, the media's SHA-256 digest, the validity verdict,
and a failure reason — `fingerprint_mismatch` when the identity could not be confirmed,
`signature_verification_failed` when the signature did not verify, or `null` when valid.

## Revocation

Revocation reasons that mean the key's private material can no longer be trusted —
`key_compromise` and `ca_compromise` — and the registry's `key_expunged` void the key's
signatures retroactively, regardless of when signed. Administrative reasons such as
`superseded` and `cessation_of_operation` are not retroactive: they void only signatures
made at or after `revoked_at`, while earlier signatures remain as trustworthy as the key's
other state allows. The contract enumerates the retroactive reasons.

## Remediation taxonomy

Authenticity and trust are separate questions. A signature is **authentic** when it is
valid, its key's revocation does not void it, and the image was signed within the key's
validity window. **Trust** asks whether a key should still sit in the kiosk's store, judged
at `audit_time`. A signature is **in-window** when the image's `signed_at` lies within the
key's validity window, inclusive of both bounds.

Each image receives exactly one action, and every quarantine carries a reason:

- A signature that is not valid is `quarantine`d under its failure reason.
- A signature voided by its key's revocation is `quarantine`d: under the revocation reason
  when that reason is retroactive, and under `signed_after_revocation` when the reason is
  administrative and the image was signed at or after `revoked_at`.
- A signature that is valid and not voided by revocation, but was made outside the key's
  validity window, is `honor_exception` when an unexpired policy exception covers it and
  `quarantine` under `signed_outside_validity` otherwise.
- An authentic image is `accept`ed when its reconciled key is currently `active`, and
  `reinstate`d when its key is no longer active.

Non-quarantine actions carry a `null` reason.

Separately, every key that is `retired` or `revoked` yet still carries a trust flag must be
removed from the store. Each such key is reported once as a `revoke_trust` key action,
ordered by `key_id`, with the key's status.

The report carries the image actions (ordered by `image_id`), the key actions, and a
summary counting each of `accept`, `reinstate`, `honor_exception`, `quarantine`, and
`revoke_trust`.
