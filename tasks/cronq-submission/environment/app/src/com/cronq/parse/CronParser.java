package com.cronq.parse;

import com.cronq.model.CronExpr;
import com.cronq.model.Field;

public final class CronParser {

    public static CronExpr parse(String line) throws ParseException {
        if (line == null) {
            throw new ParseException("null expression");
        }
        String trimmed = line.trim();
        if (trimmed.isEmpty()) {
            throw new ParseException("empty expression");
        }
        String[] parts = trimmed.split("\\s+");
        if (parts.length != 5) {
            throw new ParseException(
                "expected 5 fields, got " + parts.length + ": '" + trimmed + "'");
        }

        Field minute = FieldParser.parse(parts[0], 0, 59, null);
        Field hour = FieldParser.parse(parts[1], 0, 23, null);
        Field dom = FieldParser.parse(parts[2], 1, 31, null);
        Field month = FieldParser.parse(parts[3], 1, 12, NameTable.MONTHS);
        Field dow = FieldParser.parse(parts[4], 0, 6, NameTable.DOW);

        return new CronExpr(minute, hour, dom, month, dow, trimmed);
    }

    private CronParser() {
    }
}
