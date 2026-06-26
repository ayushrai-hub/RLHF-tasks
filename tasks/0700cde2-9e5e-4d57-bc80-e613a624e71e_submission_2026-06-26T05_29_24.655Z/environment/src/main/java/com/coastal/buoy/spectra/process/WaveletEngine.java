package com.coastal.buoy.spectra.process;

import com.coastal.buoy.spectra.model.ProcessingProfile;

import java.util.Arrays;

public final class WaveletEngine {
    private static final double RHO = 1025.0;
    private static final double G = 9.81;

    public static final class Result {
        public double significantWaveHeightM;
        public double peakPeriodS;
        public double coiMaskedRatio;
    }

    public Result analyze(double[] pressurePa, ProcessingProfile profile) {
        double mean = 0;
        for (double v : pressurePa) mean += v;
        mean /= pressurePa.length;
        double[] eta = new double[pressurePa.length];
        for (int i = 0; i < pressurePa.length; i++) {
            eta[i] = (pressurePa[i] - mean) / (RHO * G);
        }

        int n = eta.length;
        double[] scales = logScales(profile.minScale, profile.upperWaveletScale, profile.numScales);
        double sampleRate = profile.sampleRateHz;
        boolean[] timeValid = new boolean[n];
        Arrays.fill(timeValid, true);

        double maxPower = -1;
        double peakF = profile.lowHz;
        int masked = 0;

        for (int si = 0; si < scales.length; si++) {
            double scale = scales[si];
            int coiWidth = (int) Math.floor(scale / 2.0);
            for (int t = 0; t < n; t++) {
                if (t < coiWidth || t >= n - coiWidth) {
                    timeValid[t] = false;
                }
            }
            for (int t = coiWidth; t < n - coiWidth; t++) {
                double power = morletPower(eta, t, scale, sampleRate);
                double freq = 1.0 / (scale / sampleRate);
                if (freq >= profile.lowHz && freq <= profile.highHz && power > maxPower) {
                    maxPower = power;
                    peakF = freq;
                }
            }
        }

        for (boolean b : timeValid) {
            if (!b) masked++;
        }
        double m0 = 0;
        int used = 0;
        for (int t = 0; t < n; t++) {
            if (timeValid[t]) {
                m0 += eta[t] * eta[t];
                used++;
            }
        }
        m0 = used > 0 ? m0 / used : 0;

        Result r = new Result();
        r.significantWaveHeightM = 2.0 * Math.sqrt(m0);
        r.peakPeriodS = peakF > 0 ? 1.0 / peakF : 0;
        r.coiMaskedRatio = n > 0 ? (double) masked / n : 0;
        return r;
    }

    private static double[] logScales(int min, int max, int count) {
        double[] out = new double[count];
        double logMin = Math.log(min);
        double logMax = Math.log(max);
        for (int i = 0; i < count; i++) {
            double f = count == 1 ? 0 : (double) i / (count - 1);
            out[i] = Math.exp(logMin + f * (logMax - logMin));
        }
        return out;
    }

    private static double morletPower(double[] eta, int center, double scale, double sampleRate) {
        int half = (int) Math.ceil(scale * 2);
        double sum = 0;
        int cnt = 0;
        for (int k = -half; k <= half; k++) {
            int idx = center + k;
            if (idx < 0 || idx >= eta.length) continue;
            double t = k / sampleRate;
            double wavelet = Math.exp(-t * t / (2 * scale * scale)) * Math.cos(5 * t / scale);
            sum += eta[idx] * wavelet;
            cnt++;
        }
        return cnt > 0 ? sum * sum : 0;
    }
}
