double glassreef_depth_weight(int depth_m) { return depth_m < 3000 ? 1.0 : 1.0 + (depth_m - 3000) / 6000.0; }
