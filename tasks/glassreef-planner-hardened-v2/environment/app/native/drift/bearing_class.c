int glassreef_bearing_octant(double bearing_deg) { int v = (int)((bearing_deg + 22.5) / 45.0); return v % 8; }
