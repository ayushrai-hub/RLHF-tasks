The Rust application under /app emits a JSON report for a trace fold cursor, but the starter build produces values that disagree with the published contract for the stock scenario and for alternate scenarios supplied through TRACEFOLD_SEED.

Repair the program so every report matches the projection, probe, reuse, restart, and audit digest requirements in /app/data/docs/report_contract.md. Build with Cargo from /app, run the release binary, and write output to the path named by TRACEFOLD_OUT. Do not modify fixtures, contract documents, verifier assets, or hard-code scenario outputs.

All field names, invariants, codec rules, and digest constants are defined in that contract document.
