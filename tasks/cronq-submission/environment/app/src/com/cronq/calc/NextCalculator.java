package com.cronq.calc;

import com.cronq.match.Matcher;
import com.cronq.model.CronExpr;
import com.cronq.model.Field;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;

public final class NextCalculator {

    // How far ahead the search runs before giving up on a sparse expression.
    private static final int MAX_YEARS = 8;

    public static List<LocalDateTime> next(CronExpr expr, Instant from, int count) {
        List<LocalDateTime> hits = new ArrayList<>();
        if (count <= 0) {
            return hits;
        }

        LocalDateTime start = LocalDateTime.ofInstant(from, ZoneOffset.UTC)
                .withSecond(0).withNano(0);
        LocalDateTime cursor = start;
        LocalDateTime limit = start.plusYears(MAX_YEARS);

        while (hits.size() < count) {
            LocalDateTime fire = advance(expr, cursor, limit);
            if (fire == null) {
                break;
            }
            hits.add(fire);
            cursor = fire.plusMinutes(1);
        }
        return hits;
    }

    // Earliest matching time at or after `cursor` and before `limit`. Walks the
    // calendar field by field: skip whole months and days that cannot match,
    // then settle the hour and minute directly. Returns null past the horizon.
    private static LocalDateTime advance(CronExpr e, LocalDateTime t, LocalDateTime limit) {
        while (t.isBefore(limit)) {
            if (!e.month.allows(t.getMonthValue())) {
                t = t.plusMonths(1).withDayOfMonth(1).withHour(0).withMinute(0);
                continue;
            }
            if (!Matcher.dayMatches(e, t)) {
                t = t.plusDays(1).withHour(0).withMinute(0);
                continue;
            }
            int h = ceil(e.hour, t.getHour());
            if (h < 0) {
                t = t.plusDays(1).withHour(0).withMinute(0);
                continue;
            }
            if (h > t.getHour()) {
                return t.withHour(h).withMinute(0);
            }
            int m = ceil(e.minute, t.getMinute());
            if (m >= 0) {
                return t.withMinute(m);
            }
            int hn = after(e.hour, t.getHour());
            if (hn < 0) {
                t = t.plusDays(1).withHour(0).withMinute(0);
                continue;
            }
            return t.withHour(hn).withMinute(0);
        }
        return null;
    }

    // Smallest allowed value >= from, or -1 if the field has none that high.
    private static int ceil(Field f, int from) {
        for (int v : f.values()) {
            if (v >= from) {
                return v;
            }
        }
        return -1;
    }

    // Smallest allowed value strictly greater than from, or -1.
    private static int after(Field f, int from) {
        for (int v : f.values()) {
            if (v > from) {
                return v;
            }
        }
        return -1;
    }

    private NextCalculator() {
    }
}
