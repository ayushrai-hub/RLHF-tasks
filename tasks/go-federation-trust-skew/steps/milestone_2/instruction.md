Repair Go sources under `/app/environment` until bundle behavior matches `/app/environment/docs/contract.md`.

Continue from the prior window work. Prior fixes must still pass regression checks.

Operators report that assertions signed under retired bundle generations still verify after key rotation. Serial smoke on a single fresh generation still looks fine.

The verifier injects the hidden graded suite at verify time and checks integrity with `sha256sum /app/environment/internal/ward/m4_grade_test.go`; do not modify that file.

Confirm with:

```bash
go build /app/environment/...
```

Signal completion when this part passes before moving on.
