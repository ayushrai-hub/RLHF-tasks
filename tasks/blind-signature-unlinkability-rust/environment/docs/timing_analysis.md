# Timing Analysis

Timing proximity is `1 - |Δt| / max_timing_delta`. The raw value is reported as
computed; on widely separated transcripts it can run negative, which correctly
signals anti-correlation and must be preserved (do not clamp it).

The blended score weights timing as the dominant channel — `timing_weight *
correlation + (1 - timing_weight) * timing` — because temporal structure leaks
more than hash structure in practice (Danezis & Troncoso 2009, §3.4).

The representative timing figure is the **minimum** blended score across the
pairs (the best-case floor the scheme guarantees), and a pair is suspicious when
its *correlation* exceeds 0.7.
