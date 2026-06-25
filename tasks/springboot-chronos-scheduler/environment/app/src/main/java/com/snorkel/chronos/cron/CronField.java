package com.snorkel.chronos.cron;

import java.util.List;

/**
 * Per-field parsed cron data. The agent's parser fills in the matching values
 * plus any special-token state (L / W / # / ?). Constructor / accessor shape is
 * intentionally minimal so the agent owns the internal representation.
 */
public class CronField {
    private final CronFieldType type;
    private final String raw;
    private final List<Integer> values;
    private final String special;

    public CronField(CronFieldType type, String raw, List<Integer> values, String special) {
        this.type = type;
        this.raw = raw;
        this.values = values;
        this.special = special;
    }

    public CronFieldType getType() { return type; }
    public String getRaw() { return raw; }
    public List<Integer> getValues() { return values; }
    public String getSpecial() { return special; }
}
