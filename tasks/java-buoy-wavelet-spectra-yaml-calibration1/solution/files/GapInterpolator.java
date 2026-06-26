package com.coastal.buoy.spectra.process;

import com.coastal.buoy.spectra.model.PressureSample;

import java.util.Arrays;
import java.util.List;

public final class GapInterpolator {
    public double[] fill(List<PressureSample> samples, double[] pressures) {
        double[] out = Arrays.copyOf(pressures, pressures.length);
        int n = samples.size();
        for (int i = 0; i < n; i++) {
            if (samples.get(i).qualityFlag != 0) continue;
            int left = i - 1;
            while (left >= 0 && samples.get(left).qualityFlag == 0) left--;
            int right = i + 1;
            while (right < n && samples.get(right).qualityFlag == 0) right++;
            if (left >= 0 && right < n) {
                double frac = (double) (i - left) / (right - left);
                out[i] = out[left] + frac * (out[right] - out[left]);
            } else if (left >= 0) {
                out[i] = out[left];
            } else if (right < n) {
                out[i] = out[right];
            }
        }
        return out;
    }
}
