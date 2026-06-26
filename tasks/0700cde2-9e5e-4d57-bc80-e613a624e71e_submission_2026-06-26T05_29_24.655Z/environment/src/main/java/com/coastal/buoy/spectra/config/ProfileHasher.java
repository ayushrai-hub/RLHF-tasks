package com.coastal.buoy.spectra.config;

import com.coastal.buoy.spectra.model.ProcessingProfile;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

public final class ProfileHasher {
    private ProfileHasher() {}

    public static String fingerprint(ProcessingProfile profile) {
        String payload = String.format(
                Locale.US,
                "bands.high_hz=%.6f\nbands.low_hz=%.6f\ncoi_factor=%.6f\n"
                        + "drift.rate_pa_per_hour=%.6f\nreference_epoch_ms=%d\n"
                        + "sample_rate_hz=%.6f\nwavelet.max_scale=%d\nwavelet.min_scale=%d\n"
                        + "wavelet.num_scales=%d\n",
                profile.highHz,
                profile.lowHz,
                profile.coiFactor,
                profile.driftRatePaPerHour,
                profile.referenceEpochMs,
                profile.sampleRateHz,
                profile.upperWaveletScale,
                profile.minScale,
                profile.numScales);
        return sha256(payload);
    }

    public static String spectralBind(String profileFingerprint, int samplesUsed, double meanFilledPa) {
        String payload = String.format(
                Locale.US, "%s|%d|%.6f", profileFingerprint, samplesUsed, meanFilledPa);
        return sha256(payload);
    }

    private static String sha256(String payload) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(payload.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }
}
