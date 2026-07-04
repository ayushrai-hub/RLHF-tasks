#!/bin/bash
cd /app/environment
cargo run --quiet -- run --output /app/output/ledger_report.json
