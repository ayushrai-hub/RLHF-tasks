The lab CLI in /app is supposed to turn centroided mass-spectrometry exports into isotope-envelope review files, but /app/bin/msreport is still a stub. Keep it buildable with make from /app.

Milestone 1 is the centroid export. Implement `/app/bin/msreport centroid --spectra /app/data/runs --calibration /app/data/calibration.tsv --output /app/out/centroids.json` so it reads every `.tsv` spectrum file in lexical file-name order, skips rows whose `quality` is not `OK`, applies each run's calibration mz offset and intensity scale, and writes the centroid JSON.

The output is a JSON object with `runs`. Each run entry has `run`, `scan_count`, `total_ion_current`, and `scans`; each scan has `scan` and `peaks`; each peak has numeric `mz` rounded to 4 decimals and integer `intensity` rounded to the nearest integer. `total_ion_current` is the sum of those rounded peak intensities for the run. Sort runs by run id, scans by numeric scan, and peaks by mz.
