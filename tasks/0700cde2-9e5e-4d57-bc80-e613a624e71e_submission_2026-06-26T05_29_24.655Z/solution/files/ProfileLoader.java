package com.coastal.buoy.spectra.config;

import com.coastal.buoy.spectra.model.ProcessingProfile;
import org.tomlj.Toml;
import org.tomlj.TomlTable;
import org.yaml.snakeyaml.Yaml;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

public final class ProfileLoader {
    @SuppressWarnings("unchecked")
    public ProcessingProfile load(Path yamlPath, Path tomlPath) throws Exception {
        Yaml yaml = new Yaml();
        Map<String, Object> y = yaml.load(Files.readString(yamlPath));
        ProcessingProfile p = new ProcessingProfile();
        applyYaml(p, y);
        applyToml(p, Toml.parse(Files.readString(tomlPath)));
        return p;
    }

    @SuppressWarnings("unchecked")
    private void applyYaml(ProcessingProfile p, Map<String, Object> y) {
        if (y == null) return;
        if (y.get("sample_rate_hz") instanceof Number n) p.sampleRateHz = n.doubleValue();
        Map<String, Object> drift = (Map<String, Object>) y.get("drift");
        if (drift != null) {
            if (drift.get("reference_epoch_ms") instanceof Number n) p.referenceEpochMs = n.longValue();
            if (drift.get("rate_pa_per_hour") instanceof Number n) p.driftRatePaPerHour = n.doubleValue();
        }
        Map<String, Object> wavelet = (Map<String, Object>) y.get("wavelet");
        if (wavelet != null) {
            if (wavelet.get("min_scale") instanceof Number n) p.minScale = n.intValue();
            if (wavelet.get("upper_scale") instanceof Number n) p.upperWaveletScale = n.intValue();
            if (wavelet.get("num_scales") instanceof Number n) p.numScales = n.intValue();
            if (wavelet.get("coi_factor") instanceof Number n) p.coiFactor = n.doubleValue();
        }
        Map<String, Object> bands = (Map<String, Object>) y.get("bands");
        if (bands != null) {
            if (bands.get("low_hz") instanceof Number n) p.lowHz = n.doubleValue();
            if (bands.get("high_hz") instanceof Number n) p.highHz = n.doubleValue();
        }
    }

    private void applyToml(ProcessingProfile p, TomlTable root) {
        TomlTable drift = root.getTable("drift");
        if (drift != null && drift.getDouble("rate_pa_per_hour") != null) {
            p.driftRatePaPerHour = drift.getDouble("rate_pa_per_hour");
        }
        TomlTable wavelet = root.getTable("wavelet");
        if (wavelet != null && wavelet.getDouble("coi_factor") != null) {
            p.coiFactor = wavelet.getDouble("coi_factor");
        }
    }
}
