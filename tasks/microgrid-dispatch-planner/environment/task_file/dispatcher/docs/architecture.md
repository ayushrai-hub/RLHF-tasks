# Architecture

The dispatcher is a single-shot batch program. There is no state between runs
and no network access; everything it needs is on disk.

```
input_data/units.jsonl    ─┐
                           ├─►  loader  ─►  dispatch  ─►  writer  ─►  output_data/dispatch.json
input_data/config.json    ─┘
```

- **loader** deserializes the unit catalogue and the configuration into the
  structs in `types.rs`.
- **dispatch** is the only decision-making stage. It receives the full catalogue
  and configuration and returns a `Dispatch`.
- **writer** serializes the `Dispatch` as pretty JSON.

The planning evaluator (`scripts/model.py`) consumes `dispatch.json` together
with the original inputs. It is the single source of truth for how a plan is
scored; the dispatcher never imports or calls it.
