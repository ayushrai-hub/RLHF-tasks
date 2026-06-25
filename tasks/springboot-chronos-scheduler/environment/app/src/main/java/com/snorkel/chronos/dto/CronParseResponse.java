package com.snorkel.chronos.dto;

import java.util.List;

public class CronParseResponse {
    public boolean valid;
    public String error;
    public List<FieldSummary> fields;

    public static class FieldSummary {
        public String name;
        public String raw;
        public List<Integer> values;
        public String special;
    }
}
