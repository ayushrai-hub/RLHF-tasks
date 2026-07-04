# samlacsguard contract

The crate validates a normalized subset of SAML responses before an Assertion Consumer Service creates a login session. Tests use both parsed input and public structs constructed directly. All public structs, fields, and function names in `src/lib.rs` are part of the contract. The implementation must stay std-only.

## Public model

`SpPolicy` has `entity_id`, `acs_url`, `expected_in_response_to`, `trusted_issuers`, `trusted_signers`, `allowed_signature_algorithms`, `now_utc`, `clock_skew_seconds`, `require_signed_response`, `require_signed_assertion`, and `required_attributes`.

`SamlResponse` has `id`, `issuer`, `destination`, `in_response_to`, `issue_instant`, `signatures`, and `assertions`.

`SamlAssertion` has `id`, `issuer`, `subject`, `audience`, `recipient`, `in_response_to`, `not_before`, `not_on_or_after`, and `attributes`.

`Signature` has `target_id`, `signer`, and `algorithm`. A signature covers only the object whose ID exactly equals `target_id`.

`Attribute` has `name` and `value`.

`Decision.accepted` is true only when there are no denial reasons. `Decision.subject` is the accepted assertion subject. `Decision.assertion_id` is the ID of the accepted assertion or, on assertion-level denial, the ID of the first covered assertion whose checks failed.

## Input parser

`parse_response(input)` reads UTF-8 text in this normalized XML subset. Blank lines and complete whole-line XML comments are ignored. After trimming, an ignored comment line must start with `<!--` and end with `-->`; partial or unterminated comment lines are parse errors. Any parse error aborts with `ParseError { line, message }`, where `line` is 1-based and `message` is non-empty.

Every non-comment tag must appear on one line. Attributes are ASCII names followed by `="value"`; attribute order does not matter. Attribute values may contain spaces but may not contain raw `<`, `>`, or `"`.

Supported tags are:

- `<Response ID="..." Issuer="..." Destination="..." InResponseTo="..." IssueInstant="...">`
- `<Signature Target="..." Signer="..." Algorithm="..."/>`
- `<Assertion ID="..." Issuer="..." Subject="..." Audience="..." Recipient="..." InResponseTo="..." NotBefore="..." NotOnOrAfter="...">`
- `<Attribute Name="..." Value="..."/>`
- `</Assertion>`
- `</Response>`

`<Signature .../>` may appear directly under the response or inside an open assertion; in both cases it is appended to `SamlResponse.signatures` and is interpreted only by its `Target` value. `Response.ID`, `Response.Issuer`, `Response.Destination`, `Response.IssueInstant`, `Assertion.ID`, `Assertion.Issuer`, `Assertion.Subject`, `Assertion.Audience`, `Assertion.Recipient`, `Assertion.NotBefore`, `Assertion.NotOnOrAfter`, and all `Signature` fields are required. `InResponseTo` is optional on both response and assertion. Unknown tags, unknown attributes, duplicate attributes within one tag, missing required attributes, nested assertions, attributes outside assertions, signatures after `</Response>`, and unclosed response/assertion elements are parse errors. IDs may contain ASCII letters, digits, `_`, `-`, `.`, and `:`.

## Time

Timestamps are UTC and must be exactly `YYYY-MM-DDTHH:MM:SSZ`. Calendar validation is real: month lengths and leap years matter. `clock_skew_seconds` extends the validity window by that many seconds on both sides. `NotBefore` is inclusive after skew. `NotOnOrAfter` is exclusive after skew.

## Validation

`validate_response(policy, response)` returns denial reasons in this order:

1. `malformed-time`
2. `duplicate-id`
3. `untrusted-issuer`
4. `destination-mismatch`
5. `request-id-mismatch`
6. `response-signature-required`
7. `assertion-signature-required`
8. `untrusted-signature`
9. `weak-signature-algorithm`
10. `assertion-not-yet-valid`
11. `assertion-expired`
12. `audience-mismatch`
13. `recipient-mismatch`
14. `subject-missing`
15. `attribute-missing:NAME`

Response and assertion issuers must appear in `trusted_issuers`. `Response.destination` and assertion `recipient` must exactly equal `policy.acs_url`. Assertion `audience` must exactly equal `policy.entity_id`. If `policy.expected_in_response_to` is present, response and assertion `in_response_to` must both equal it. If `policy.expected_in_response_to` is absent, absent response and assertion `in_response_to` values are allowed.

Validation has explicit gates. If any timestamp is malformed, return exactly `malformed-time` with no assertion ID. Otherwise, if any response or assertion ID duplicates an earlier ID, including the response ID, return exactly `duplicate-id` with no assertion ID. Next collect response-level `untrusted-issuer`, `destination-mismatch`, and `request-id-mismatch` reasons in the documented order; if any are present, return them and do not run signature or assertion checks.

Signatures are evaluated by target ID, not by position. A signature is trusted only when `signer` appears in `trusted_signers` and `algorithm` appears in `allowed_signature_algorithms`. A response signature targets `response.id`; an assertion signature targets an assertion ID. Target matching is exact, case-sensitive, and not prefix or suffix based. If response signing is required and no signature targets `response.id`, deny with `response-signature-required`. If a signature targets `response.id` and every relevant response signature is untrusted or weak, deny with `untrusted-signature` or `weak-signature-algorithm` even when `require_signed_response` is false; that flag only controls whether a missing response signature is allowed. If assertion signing is required, only assertions with a valid signature targeting that assertion ID can be selected. If no signature targets any assertion ID, deny with `assertion-signature-required`.

If a relevant response or assertion signature exists but every relevant signature has an untrusted signer, deny with `untrusted-signature`. If a relevant signature has a trusted signer but every trusted relevant signature uses a disallowed algorithm, deny with `weak-signature-algorithm`. At least one relevant signature with a trusted signer and allowed algorithm makes that target valid even if other signatures for the same target are untrusted or weak.

The validator must not accept an unsigned or wrongly signed assertion just because another response/assertion is signed. To prevent signature wrapping, it evaluates covered assertions only. When assertion signing is required, a covered assertion is one with a valid signature targeting that assertion ID. When assertion signing is not required, a valid response signature covers all assertions, and a valid assertion signature also covers its own assertion. Among covered assertions, accept the first assertion in input order that satisfies all assertion checks. If no covered assertion is valid, return every applicable denial reason for the first covered assertion in the global order above; do not stop after the first assertion-level reason. A response with zero assertions is denied with `assertion-signature-required`, even when `require_signed_assertion` is false.

Attributes are matched by exact `name`; at least one attribute with that name must exist for every `policy.required_attributes` item.

## Audits

`audit_response(response)` emits findings in this order:

- `ERROR duplicate-id:ID`
- `ERROR signature-target-missing:ID`
- `WARN unsigned-response`
- `WARN unsigned-assertion:ID`
- `WARN weak-signature-algorithm:ALGORITHM`
- `WARN empty-subject:ID`

Duplicate ID findings are emitted in duplicate discovery order, once for each duplicate ID occurrence after the first occurrence of that ID. The response ID participates in this set, so an assertion with the same ID as the response emits `ERROR duplicate-id:RESPONSE_ID`; later duplicate assertions emit another finding for each later duplicate occurrence. Signature target findings are emitted in signature order whenever the target ID does not exist, including repeated missing target IDs. `WARN unsigned-response` is emitted when no signature targets the response ID. `WARN unsigned-assertion:ID` is emitted once for each unsigned assertion ID, even if that ID appears on multiple unsigned assertions. Weak algorithm findings are emitted in signature order for `rsa-sha1`, `dsa-sha1`, and `sha1`.

`summary_lines(response)` returns one response line followed by one assertion line per assertion:

`response ID issuer=ISSUER assertions=N signatures=N`

`assertion ID issuer=ISSUER subject=yes|no attrs=N`
