# Timing bounds

Record fractional-second wall times for all three benchmark phases. All duration fields in the release benchmark JSON must be greater than zero. Sub-second warm builds must not truncate to zero.

Cold must look like a first fill: no prior cache hits and a non-zero miss count, with timing that reflects a multi-crate compile of several seconds. Warm must finish in less than half the cold duration with zero misses and zero compilations in its phase counters. Post-clean must show cache hits strictly greater than compilations and at least as many hits as cold recorded misses after local `target/` trees are gone. Replay capture must corroborate remote-cache reads on verification.
