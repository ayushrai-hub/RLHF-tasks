package com.coastal.buoy.spectra.process;

import com.coastal.buoy.spectra.model.PressureSample;
import com.coastal.buoy.spectra.model.ProcessingProfile;

import java.util.List;

public final class DriftCorrector {
    public double[] correct(List<PressureSample> samples, ProcessingProfile profile) {
        double[] out = new double[samples.size()];
        double sum = 0;
        for (int i = 0; i < samples.size(); i++) {
            double hours = (samples.get(i).timestampMs - profile.referenceEpochMs) / 3_600_000.0;
            double adj = profile.driftRatePaPerHour * hours;
            out[i] = samples.get(i).pressureHpa + adj;
            sum += Math.abs(adj);
        }
        return out;
    }

    public double meanCorrection(List<PressureSample> samples, ProcessingProfile profile) {
        double sum = 0;
        for (PressureSample s : samples) {
            double hours = (s.timestampMs - profile.referenceEpochMs) / 3_600_000.0;
            sum += Math.abs(profile.driftRatePaPerHour * hours);
        }
        return samples.isEmpty() ? 0 : sum / samples.size();
    }
}
