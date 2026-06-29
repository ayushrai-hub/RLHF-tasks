The Rust CLI in `/app` turns an offline kettle-temperature/power-mode event log into a process-kettle element cycle ledger: the intervals during which the heating element was ON. It currently reports interval boundaries as if the element could switch immediately whenever demand changes. Fix `/app/src` so `kettleheat` reads one JSON document from stdin, or from a file path given as the first argument, and writes the corrected ledger as one JSON document to stdout.

`/app/docs/spec.md` is the single source of truth for the exact input format and for every control and interval rule: the document's JSON keys are the canonical keys already parsed by `/app/src/parse.rs` (`targetTemp`, `deadband`, `minRun`, `minRest`, `until`, and events with `type`/`at`). Do not rename the input schema while fixing the control behavior.

Write a single JSON object:

```
{
  "intervals": [ { "start": <int>, "end": <int> } ],
  "ontime": <int>,
  "final": { "state": "on"|"off", "since": <int> }
}
```

- `intervals` is ordered by time and non-overlapping; every interval has `start < end`, so zero-length intervals are not emitted.
- `ontime` is the sum of `end - start` over all emitted intervals.
- `final` reports the element state at the horizon and the timestamp at which the element last entered that state; if the element is off and never produced an ON interval, `final.since` is `0`.

Also preserve the existing CLI behavior:

- `until` is a hard ceiling: never emit any timestamp past the horizon.
- Output must be deterministic: the same input always produces the same ledger.
- Malformed input must print `error: <message>` to stderr, write nothing to stdout, and exit nonzero.
