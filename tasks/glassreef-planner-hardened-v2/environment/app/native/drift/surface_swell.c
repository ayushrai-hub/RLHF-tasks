int glassreef_swell_bucket(double swell_m) { return swell_m < 1.5 ? 0 : (swell_m < 2.5 ? 1 : 2); }
