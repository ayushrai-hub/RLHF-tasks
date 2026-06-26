Repair Go sources under `/app/environment` until binding and alias behavior matches `/app/environment/docs/contract.md` and `/app/environment/docs/api.md`.

Continue from prior window and bundle work. Both must still pass regression checks.

Operators report equivalent service host spellings mismatch during realm binding, and external id resolution returns principals from before the latest map reload under concurrent reload stress. Serial probe may report `"ready": true` while graded binding and alias cases still fail.

The verifier rewrites `/app/output/stage/probe.json` (`ready`, `code`, `principal`) and `/app/output/harness/status.txt` (`harness_ok`). Hand-written output is insufficient. The verifier runs `pytest --ctrf /logs/verifier/ctrf.json` over the graded suite and checks integrity with `sha256sum /app/environment/internal/ward/m4_grade_test.go`; do not modify that file.

Confirm with:

```bash
go build /app/environment/...
bash /app/environment/scripts/verify_output.sh
/app/bin/probe
```

Signal completion when this part passes before moving on.
