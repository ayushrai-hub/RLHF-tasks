# Sigil Capability Tokens — Internal Format Spec

Status: active (migration in progress)
Audience: platform engineers implementing or operating the `warden` access checker

Sigils are bearer capability tokens. A token names a subject and carries a list of
*caveats* — restrictions that must all hold for a request to be authorized. Anyone
holding a token may further restrict it (add caveats) before passing it on, but no
holder can broaden it without the issuing key.

Two token versions exist while we migrate off the old gateway:

- **v1** — current format. HMAC-SHA256 chained tags. This is what `warden` issues and checks.
- **v0** — legacy format still honored by the old gateway's checker (`/app/legacy/verify.go`).
  We keep accepting v0 only until the gateway is retired.

---

## 1. Encoding primitives

- `b64(x)` — base64url of the bytes `x` using the alphabet `A–Z a–z 0–9 - _`, with **no
  `=` padding**. Decoding accepts only this alphabet.
- `hex(x)` — lowercase hexadecimal.
- `HMAC(k, m)` — HMAC-SHA256 with key `k` over message `m`, 32-byte output.
- `SHA256(m)` — 32-byte digest.
- Strings are UTF-8. Caveat strings are restricted to printable ASCII (bytes `0x20`–`0x7E`).
- Integers in caveat arguments are decimal, base 10, no sign, no leading zeros.

---

## 2. v1 token

### 2.1 Wire format

A v1 token is a single line of four dot-separated fields:

```
v1.<id>.<caveats>.<tag>
```

| Field | Value |
| --- | --- |
| `v1` | literal version marker |
| `<id>` | `b64(` subject id bytes `)` |
| `<caveats>` | the caveats, each `b64(` caveat-string `)`, joined by `~`. Empty when there are no caveats. |
| `<tag>` | `b64(` 32-byte authentication tag `)` |

A caveat-string has the form `type=argument` (a single `=` separates a lowercase `type`
from its `argument`; the argument may itself contain `=`).

### 2.2 Tag construction

The tag authenticates the id and the exact ordered list of caveat-strings. It is a chain:

```
sig₀   = HMAC(rootKey, "sigil/v1\x00id\x00"  ‖ idBytes)
sigᵢ   = HMAC(sigᵢ₋₁,  "sigil/v1\x00cav\x00" ‖ caveatᵢ)     for i = 1..n
tag    = sigₙ
```

`‖` is byte concatenation. `caveatᵢ` is the raw caveat-string bytes (before base64). The
two quoted strings are fixed domain-separation prefixes. Each link's HMAC key is the
*previous* tag, never the root key.

### 2.3 Caveat types

A request is described by a context: the current time `now` (unix seconds), and optionally
a request `path`, `method`, and client `ip` (IPv4). Each caveat constrains the context.

| `type` | argument | holds iff |
| --- | --- | --- |
| `exp` | unix seconds `t` | `now < t` (strict) |
| `nbf` | unix seconds `t` | `now >= t` |
| `path` | an absolute path prefix `p` | the request path is *at or below* `p` by path segments (§2.4) |
| `method` | comma-separated method names | the request method, compared case-insensitively, is one of them |
| `cidr` | IPv4 `a.b.c.d/len` | the client ip is inside the block (`0 <= len <= 32`) |

When the same `type` appears more than once, **all** occurrences must hold (restrictions
only ever narrow; they never widen). If a caveat needs a context field the request did not
supply (e.g. a `path` caveat but no request path), the caveat does not hold. Empty entries
in a `method` list (e.g. a trailing comma) are ignored.

Any caveat whose `type` is not in the table above causes verification to **fail**. A token
is never authorized on the basis of a caveat the checker does not understand.

### 2.4 Path-segment containment

Split both paths on `/` and drop empty segments. Path `p` *contains* request `r` when the
segment list of `p` is a leading prefix of the segment list of `r`. Thus `path=/a/b`
contains `/a/b` and `/a/b/c` but not `/a/bc` and not `/a`. `path=/` (no segments) contains
everything. Trailing slashes are not significant.

### 2.5 Verification

Given `rootKey`, a token, a request context, and zero or more discharge sigils, the token is
authorized iff:

1. The token parses as four fields with a 32-byte tag.
2. The tag recomputed per §2.2 equals the token's tag. (Use a constant-time comparison.)
3. Every first-party caveat holds against the context per §2.3.
4. Every third-party caveat (§2.6) is satisfied by a supplied discharge.

On success the checker reports the **effective scope**: the `path` argument with the most
segments among the token's first-party `path` caveats (in a token that authorizes the request
these are nested, so the most-specific one is well defined); if there is none, `/`.

### 2.6 Third-party caveats

A caveat may defer a check to a third party with whom the issuer shares a 32-byte key
`tpKey`. Its caveat-string has type `third` and a structured argument:

```
third=<location>|<predicate>|<cid>|<vid>
```

`<location>` and `<predicate>` are printable ASCII containing no `|`; `<cid>` and `<vid>` are
each `b64(` a 32-byte value `)`. The verifier does not interpret `<predicate>` — the third
party turns it into the discharge's own caveats.

**Issuing.** Let `sig` be the chain value immediately *before* this caveat (the current tag),
and `pred` the predicate bytes:

```
cK  = SHA256("sigil/v1\x00ck\x00"  ‖ tpKey ‖ sig  ‖ pred)
vid = cK XOR SHA256("sigil/v1\x00vid\x00" ‖ sig)
cid = cK XOR SHA256("sigil/v1\x00cid\x00" ‖ tpKey ‖ pred)
```

The resulting caveat-string is chained like any other caveat (§2.2).

**Discharge.** The third party recovers
`cK = cid XOR SHA256("sigil/v1\x00cid\x00" ‖ tpKey ‖ pred)` and issues a discharge sigil — a
token rooted at `cK` whose id is the 32-byte `cid` and whose caveats are first-party caveats
(§2.3) enforcing the predicate. It has the same chain as §2.2 with the marker `disch`:

```
disch.<id>.<caveats>.<tag>          id = b64(cid)
dsig₀ = HMAC(cK,  "sigil/v1\x00id\x00"  ‖ cid)
dsigᵢ = HMAC(dsigᵢ₋₁, "sigil/v1\x00cav\x00" ‖ caveatᵢ)
```

**Binding.** Before a discharge is presented with a particular root token it is bound to it:

```
boundTag = HMAC(rootTag, "sigil/v1\x00bind\x00" ‖ dischTag)
```

where `rootTag` is the root token's tag and `dischTag` the discharge's tag; the discharge's
tag field is replaced with `boundTag`.

**Verifying.** Walking the root chain, for each `third=` caveat the verifier recovers
`cK = vid XOR SHA256("sigil/v1\x00vid\x00" ‖ sig)` using the chain value `sig` before that
caveat. It then requires a supplied discharge whose id equals this caveat's `cid` such that
(a) re-deriving that discharge's tag from `cK` and its caveats, the supplied discharge's tag
equals `HMAC(rootTag, "sigil/v1\x00bind\x00" ‖ that tag)`, and (b) every caveat on the
discharge holds against the request context (§2.3). A root token with any undischarged,
mis-bound, or unsatisfied third-party caveat is not authorized.

---

## 3. v0 legacy token

The old gateway issued v0 tokens and still verifies them with the checker whose source is
at `/app/legacy/verify.go`. We do not have the gateway's signing key; it is a 32-byte
secret held only by the gateway. Its length (32 bytes) is public.

### 3.1 Wire format

```
v0.<body>.<tag>
```

| Field | Value |
| --- | --- |
| `v0` | literal version marker |
| `<body>` | `b64(` body bytes `)` |
| `<tag>` | `hex(` `SHA256(serverKey ‖ bodyBytes)` `)` |

### 3.2 Body grammar and the legacy checker

The body is a sequence of lines separated by `\n` (`0x0A`). The legacy checker:

- considers only lines that are wholly printable ASCII and of the form `scope=/...`
  (a value beginning with `/`) or `exp=<digits>`; every other line is ignored;
- takes the **last** surviving `scope=` line as the granted scope and the **last**
  surviving `exp=` line as the expiry;
- authorizes a request for path `r` iff the granted scope contains `r` by path segments
  (§2.4) and `now < exp`;
- recomputes `SHA256(serverKey ‖ bodyBytes)` and rejects the token unless it equals `<tag>`.

The gateway never reveals `serverKey`; a v0 token is accepted purely on the tag matching.

---

## 4. The warden command

`warden` is a single binary at `/app/warden`. A token argument may instead be `-` to read
from standard input. Keys are hex on the command line. Each subcommand writes one line to
stdout. A third-party caveat is given to `mint`/`attenuate` as `<location>|<predicate>|<tpKey
hex>`. First-party caveats are applied in the order listed, then third-party caveats.

```
warden verify --key <hex> [--now <unix>] [--path <p>] [--method <m>] [--ip <a.b.c.d>] [--discharge <disch>]... <token>
warden mint --key <hex> --id <id> [--caveat <type=arg>]... [--third <loc|pred|tpkeyhex>]...
warden attenuate [--caveat <type=arg>]... [--third <loc|pred|tpkeyhex>]... <token>
warden discharge --tpkey <hex> --predicate <p> --cid <b64> [--caveat <type=arg>]...
warden bind <root-token> <discharge>
```

- `verify` exits 0 and prints `OK <effective-scope>` (§2.5) when the token is valid and
  authorized, non-zero otherwise. Context flags may be omitted when no caveat needs them.
  `--discharge` supplies bound discharge sigils for third-party caveats.
- `mint` prints a new token; `attenuate` prints the input token with caveats appended and
  must work for a holder who has only the token and not the root key.
- `discharge` prints a discharge sigil for the caveat key recovered from `--cid`; `bind`
  prints a discharge bound to the given root token.

## 5. Notes

- `warden` takes keys as hex command-line arguments; it does not read keys from disk.
- Tokens are single-line and contain no whitespace.
- A v0 token captured from the old gateway is at `/app/captured.sigil`.
