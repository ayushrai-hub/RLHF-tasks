# Operator contract

The package pipeline compiles the C targets, installs them below the active prefix, and records an audit manifest after the install step completes. The manifest is generated output; it is not a source artifact checked into the tree.

Release audits are meant to describe what a fresh consumer receives from the install prefix. Build-tree commands may rely on compile-time loader behavior, ambient library directories, or source-tree compatibility headers while developers iterate locally. Those shortcuts can produce plausible intermediate output, but they are not acceptable release evidence.

Each successful package or replay run also updates `/app/work/capsule/install_ledger.json`. The ledger records the manifest generation counter, the active catalog epoch, and the digest of the last manifest file. The manifest carries a matching `ledger` section that must stay aligned with the sidecar ledger and with the installed tree.

The `tree_root_sha256` field is the lowercase SHA-256 hex digest of the UTF-8 string formed by sorting every `path:sha256` pair from the manifest `tree` section and joining them with newline characters. Reconcile compares that digest against a recomputation from the manifest tree rather than from raw directory walks alone.

Fresh package runs rebuild the install prefix from scratch. Replay runs reinstall from the existing build directory without bumping the ledger generation. Reconcile validates manifest, ledger, and tree-root consistency for the current install prefix.

Downstream jobs read `/app/output/install_manifest.json` and compare installed command metadata with the installed header and package-config records. Maintainers normally verify install artifacts rather than relying on a build-directory smoke result alone.
