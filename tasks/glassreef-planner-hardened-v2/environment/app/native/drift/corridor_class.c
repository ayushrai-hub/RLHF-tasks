int glassreef_corridor_risk(double mean_mps) { return mean_mps > 1.4 ? 3 : (mean_mps > 0.9 ? 2 : 1); }
