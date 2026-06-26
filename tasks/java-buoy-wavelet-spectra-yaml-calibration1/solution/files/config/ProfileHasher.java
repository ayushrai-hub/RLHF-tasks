package com.coastal.buoy.spectra.config;

import com.coastal.buoy.spectra.model.ProcessingProfile;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Locale;

public final class ProfileHasher {
    private ProfileHasher() {}

    public static String fingerprint(ProcessingProfile profile) {
        String[] lines = {
            String.format(Locale.US, "bands.high_hz=%.6f", profile.highHz),
            String.format(Locale.US, "bands.low_hz=%.6f", profile.lowHz),
            String.format(Locale.US, "coi_factor=%.6f", profile.coiFactor),
            String.format(Locale.US, "drift.rate_pa_per_hour=%.6f", profile.driftRatePaPerHour),
            String.format(Locale.US, "reference_epoch_ms=%d", profile.referenceEpochMs),
            String.format(Locale.US, "sample_rate_hz=%.6f", profile.sampleRateHz),
            String.format(Locale.US, "wavelet.max_scale=%d", profile.upperWaveletScale),
            String.format(Locale.US, "wavelet.min_scale=%d", profile.minScale),
            String.format(Locale.US, "wavelet.num_scales=%d", profile.numScales),
        };
        Arrays.sort(lines);
        return sha256(String.join("\n", lines) + "\n");
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
