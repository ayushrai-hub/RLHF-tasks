# Trace desk troubleshooting

Symptom: index counts look low even though Markdown bundles contain multiple fenced excerpts per file.

The desk ships several Gradle modules. Only the harvest CLI wired through `q7cli` feeds `milestone_probes.sh`; auxiliary packages under `r5decoy` count headings for unrelated CI smoke and do not lift trace fences.

Symptom: audit shows missing peers when strace uses hexadecimal service ports.

Re-read `/app/docs/strace_contract.md` for `htons` literal forms and IPv6 field names; decimal-only parsing drops relay-lane excerpts.

Symptom: lsof paths outside the run directory are ignored when inode rows show `(deleted)`.

Re-read `/app/docs/lsof_contract.md` for stale path suffix handling before comparing against `run_dir`.

Contracts: `docs/index_contract.md`, `docs/strace_contract.md`, `docs/lsof_contract.md`, `docs/audit_contract.md`, `docs/cleanup_contract.md`, `docs/verification_contract.md`
