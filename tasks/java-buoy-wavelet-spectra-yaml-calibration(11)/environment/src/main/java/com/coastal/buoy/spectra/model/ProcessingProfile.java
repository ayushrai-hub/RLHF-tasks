package com.coastal.buoy.spectra.model;

public final class ProcessingProfile {
    public double sampleRateHz = 2.0;
    public long referenceEpochMs;
    public double driftRatePaPerHour;
    public int minScale = 2;
    public int upperWaveletScale = 32;
    public int numScales = 16;
    public double coiFactor = 1.4142135623730951;
    public double lowHz = 0.05;
    public double highHz = 0.45;
}
