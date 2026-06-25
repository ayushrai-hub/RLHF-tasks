package com.cronq.parse;

import java.util.HashMap;
import java.util.Map;

public final class NameTable {
    public static final Map<String, Integer> MONTHS = new HashMap<>();
    public static final Map<String, Integer> DOW = new HashMap<>();

    static {
        String[] months = {"JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                            "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"};
        for (int i = 0; i < months.length; i++) {
            MONTHS.put(months[i], i + 1);
        }
        String[] days = {"SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"};
        for (int i = 0; i < days.length; i++) {
            DOW.put(days[i], i);
        }
    }

    private NameTable() {
    }
}
