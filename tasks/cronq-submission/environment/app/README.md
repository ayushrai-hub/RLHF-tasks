A tiny command-line cron evaluator. Give it a five-field expression and a
starting time, get back the next few times it fires.

```sh
./build.sh
java -jar cronq.jar next --expr "0 9 * * MON-FRI" --from "2026-03-01T00:00:00Z" --count 5
```

The expression format, the day-of-month / day-of-week rule, and the output
schema are written up in `docs/PROTOCOL.md`. `docs/ARCHITECTURE.md` has the
module layout. Bundled example cases live in `data/cases/`, with reference
outputs for some of them in `data/manifest.json`.

No external dependencies -- just a JDK.
