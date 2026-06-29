Cursor continuation
-------------------

The JSON index action returns a response header carrying the next batch token when more rows remain. Client code must advance using that header value on subsequent requests. The response body also carries a token field; those two channels are not always identical after a retry sequence.

The authoritative filter window uses a half-open end: rows with `recorded_at` equal to the requested `until` instant are excluded.
