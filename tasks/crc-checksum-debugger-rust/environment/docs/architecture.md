# Relay Audit Tool Architecture

## Overview

The Relay Audit Tool validates packet integrity across a multi-stage
relay network by replaying journal events and cross-validating checksums.

## Configuration Hierarchy

Per ITU-T X.224 Annex B, configuration is resolved in this priority:
1. Override file (relay_overrides.toml) — field deployment params
2. Base config (relay.toml) — factory defaults
3. Compile-time constants (build.rs) — bare-metal fallback

The override file is authoritative for field-deployed relay nodes.

## Journal Replay

Per ITU-T X.224 §6.2.1, entries are captured in timestamp order.
The replay engine processes them in this order and combines hashes
using wrapping addition (per §6.3.1) which preserves ordering
information for replay attack detection.

## Independent Verification Mode

Per NIST SP 800-155 §4.1.3, independent verification bypasses chain
dependencies for parallel processing. The standard init is always used.
