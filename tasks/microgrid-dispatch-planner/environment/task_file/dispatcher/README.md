# dispatcher

A small Rust binary that reads the unit catalogue and the dispatch
configuration, decides how to run each distributed energy resource (and the
network-wide frequency setpoint), and writes the plan to
`output_data/dispatch.json`.

```
cargo build --release
./target/release/dispatcher
```

The binary takes no arguments. Input and output paths are fixed:

- reads `/app/task_file/input_data/units.jsonl`
- reads `/app/task_file/input_data/config.json`
- writes `/app/task_file/output_data/dispatch.json`

The dispatch logic lives in `src/dispatch.rs`. The loader, writer, and entry
point are complete; only `dispatch.rs` needs work.

## Layout

| file              | role                                          |
| ----------------- | --------------------------------------------- |
| `src/main.rs`     | entry point; wires loader -> dispatch -> writer |
| `src/loader.rs`   | parses `units.jsonl` and `config.json`        |
| `src/types.rs`    | `Unit`, `Config`, `Dispatch` structs          |
| `src/dispatch.rs` | **the dispatch strategy (edit this)**         |
| `src/writer.rs`   | serializes the `Dispatch` to JSON             |

See `docs/` for the data flow and the scoring overview.
