package com.coastal.buoy.spectra.process;

import com.coastal.buoy.spectra.model.PressureSample;

import java.util.Arrays;
import java.util.List;

public final class GapInterpolator {
    public double[] fill(List<PressureSample> samples, double[] pressures) {
        double[] out = Arrays.copyOf(pressures, pressures.length);
        for (int i = 0; i < samples.size(); i++) {
            if (samples.get(i).qualityFlag == 0) {
                out[i] = 0.0;
            }
        }
        return out;
    }
}
