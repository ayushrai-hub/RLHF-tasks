# Verified envelope staging

Milestone 1 splits verify and commit. m1-verify checks the signature and writes staging; m1-commit updates workflow state from staging only; m1 runs both.

## Staging path

/app/state/ota/verified-envelope.json — pretty-printed JSON, sorted keys, trailing newline.

Fields: device (string), envelope (full object), epoch (integer), verified (boolean, true after verify).

m1-verify must not bump workflow_generation, mutate state.json, or truncate the apply journal. Only m1-commit and m1 may do that.

## Signature preimage

Pipe-separated, in order: version, device, build_id, epoch, payload_sha256, epoch-key string. Assembly is in /app/src/sig_canon.rs before SHA-256.
