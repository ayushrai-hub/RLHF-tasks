Keep the /app mass-spectrometry CLI buildable with make from /app. Milestone 2 adds isotope-envelope detection, and the centroid command from the previous milestone should still work.

Implement `/app/bin/msreport envelopes --centroids /app/out/centroids.json --policy /app/data/isotope_policy.csv --output /app/out/envelopes.json`. For each policy row, use matching peaks in the mz window for that run and scan, build the longest chain whose adjacent mz spacing is within 0.015 of `1.003355 / charge`, break equal-length chain ties by the highest total intensity, and skip rows that do not reach `min_peaks`.

Write a JSON object with `envelopes` sorted by family and then run. Each envelope has `family`, `run`, integer `scan`, integer `charge`, integer `peak_count`, numeric `monoisotopic_mz`, numeric `neutral_mass`, integer `intensity_sum`, and `peak_mz`. Round mz values to 4 decimals and neutral mass to 5 decimals; neutral mass is `(monoisotopic_mz - 1.007276466812) * charge`.
