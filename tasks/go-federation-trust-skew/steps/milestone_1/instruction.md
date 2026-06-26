Repair Go sources under `/app/environment` until behavior matches `/app/environment/docs/contract.md` and `/app/environment/docs/api.md`.

Operators report that monotonic anchors near the edges of the configured validity interval flip between admitted and denied while anchors well inside the interval look fine on serial probe checks.

The verifier injects the hidden graded suite at verify time and checks integrity with `sha256sum /app/environment/internal/ward/m4_grade_test.go`; do not modify that file.

Confirm with:

```bash
go build /app/environment/...
```

Signal completion when this part passes before moving on.
