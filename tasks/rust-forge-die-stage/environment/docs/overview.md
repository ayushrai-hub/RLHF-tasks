# Forge die stage driver

The forge die stage binary replays operator journals against FDIE imprint blocks on disk.
Each block stores a die identifier and a tonnage reading from the last press cycle.
Forge epochs advance when a new staging window opens; journal revisions track durable ledger mutations.

Recovery mode replays against the frozen snapshot under `/app/snapshot/forge_baseline.json`.
The registry probe exercises the in-process die registry cache used by operator summaries.
