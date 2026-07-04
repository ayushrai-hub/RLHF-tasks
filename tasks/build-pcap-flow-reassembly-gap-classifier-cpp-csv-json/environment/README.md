# Flowgap

Flowgap is a small command-line analyzer for exported TCP packet metadata. It is intentionally built from CSV rows rather than pcap bytes so responders can run it in restricted environments where capture libraries are not installed.

The production entrypoint builds `/app/bin/flowgap` from `/app/src/main.cpp` and writes a compact JSON report for the fixture in `/app/input/packets.csv`.
