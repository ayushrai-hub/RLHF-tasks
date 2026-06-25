#!/usr/bin/env bash
# Oracle for milestone 1 — full Quartz-dialect cron parser + nextExecutionTime.
# Self-contained: writes every file from scratch so re-running the script
# under a fresh container works.
set -euo pipefail

cd /app

# ---------- QuartzCronExpression.java ----------
cat > /app/src/main/java/com/snorkel/chronos/cron/QuartzCronExpression.java <<'JAVA'
package com.snorkel.chronos.cron;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.TreeSet;

/**
 * Quartz-dialect 6-field cron parser. Fields: seconds minutes hours
 * dayOfMonth month dayOfWeek. Day-of-week values follow the Quartz
 * convention: 1=SUN ... 7=SAT (or SUN..SAT case-insensitive).
 */
public class QuartzCronExpression {

    private final String expression;
    private final List<CronField> fields;
    private final FieldSpec seconds;
    private final FieldSpec minutes;
    private final FieldSpec hours;
    private final DomSpec dayOfMonth;
    private final FieldSpec month;
    private final DowSpec dayOfWeek;

    private QuartzCronExpression(String expression, List<CronField> fields,
                                  FieldSpec seconds, FieldSpec minutes, FieldSpec hours,
                                  DomSpec dom, FieldSpec month, DowSpec dow) {
        this.expression = expression;
        this.fields = fields;
        this.seconds = seconds;
        this.minutes = minutes;
        this.hours = hours;
        this.dayOfMonth = dom;
        this.month = month;
        this.dayOfWeek = dow;
    }

    public String getExpression() { return expression; }
    public List<CronField> getFields() { return fields; }

    public static QuartzCronExpression parse(String expression) {
        if (expression == null) throw new CronParseException("expression is null");
        String trimmed = expression.trim();
        if (trimmed.isEmpty()) throw new CronParseException("expression is empty");
        String[] parts = trimmed.split("\\s+");
        if (parts.length != 6 && parts.length != 7) {
            throw new CronParseException("expression must have 6 or 7 fields, got " + parts.length);
        }
        FieldSpec seconds = parseSimple(parts[0], CronFieldType.SECONDS);
        FieldSpec minutes = parseSimple(parts[1], CronFieldType.MINUTES);
        FieldSpec hours = parseSimple(parts[2], CronFieldType.HOURS);
        DomSpec dom = parseDom(parts[3]);
        FieldSpec monthF = parseSimple(normalizeMonth(parts[4]), CronFieldType.MONTH);
        DowSpec dow = parseDow(parts[5]);

        if ("?".equals(parts[3]) && "?".equals(parts[5])) {
            throw new CronParseException("exactly one of dayOfMonth and dayOfWeek must be ?");
        }
        if (!"?".equals(parts[3]) && !"?".equals(parts[5])) {
            throw new CronParseException("exactly one of dayOfMonth and dayOfWeek must be ?");
        }

        List<CronField> publicFields = new ArrayList<>();
        publicFields.add(new CronField(CronFieldType.SECONDS, parts[0], asList(seconds.values), seconds.special));
        publicFields.add(new CronField(CronFieldType.MINUTES, parts[1], asList(minutes.values), minutes.special));
        publicFields.add(new CronField(CronFieldType.HOURS,   parts[2], asList(hours.values),   hours.special));
        publicFields.add(new CronField(CronFieldType.DAY_OF_MONTH, parts[3], asList(dom.values), dom.special));
        publicFields.add(new CronField(CronFieldType.MONTH,   parts[4], asList(monthF.values), monthF.special));
        publicFields.add(new CronField(CronFieldType.DAY_OF_WEEK, parts[5], asList(dow.values), dow.special));
        return new QuartzCronExpression(expression, publicFields, seconds, minutes, hours, dom, monthF, dow);
    }

    private static List<Integer> asList(TreeSet<Integer> s) { return new ArrayList<>(s); }

    public ZonedDateTime nextExecutionTime(ZonedDateTime from) {
        if (from == null) throw new IllegalArgumentException("from is null");
        ZoneId zone = from.getZone();
        LocalDateTime startLocal = from.toLocalDateTime().plusSeconds(1).withNano(0);
        LocalDateTime found = findNext(startLocal);
        if (found == null) return null;
        return resolveLocal(found, zone);
    }

    public ZonedDateTime nextExecutionTime(ZonedDateTime from, ZoneId zone) {
        return nextExecutionTime(from.withZoneSameInstant(zone));
    }

    private LocalDateTime findNext(LocalDateTime start) {
        int year = start.getYear();
        int maxYear = year + 8;
        LocalDateTime cursor = start;
        while (cursor.getYear() <= maxYear) {
            LocalDateTime nxt = advance(cursor);
            if (nxt != null) return nxt;
            cursor = LocalDateTime.of(cursor.getYear() + 1, 1, 1, 0, 0, 0);
        }
        return null;
    }

    private LocalDateTime advance(LocalDateTime cursor) {
        for (int safety = 0; safety < 20000; safety++) {
            int y = cursor.getYear();
            int mo = cursor.getMonthValue();
            int dom = cursor.getDayOfMonth();
            int h = cursor.getHour();
            int mi = cursor.getMinute();
            int se = cursor.getSecond();

            if (!month.values.contains(mo)) {
                Integer nextMonth = month.values.ceiling(mo);
                if (nextMonth == null) return null;
                cursor = LocalDateTime.of(y, nextMonth, 1, 0, 0, 0);
                continue;
            }

            int candidateDom;
            if (dayOfMonth.isQuestion()) {
                candidateDom = dayOfWeek.firstDomOnOrAfter(y, mo, dom);
            } else {
                candidateDom = dayOfMonth.firstDomOnOrAfter(y, mo, dom);
            }
            if (candidateDom < 0) {
                cursor = LocalDateTime.of(y, mo, 1, 0, 0, 0).plusMonths(1);
                continue;
            }
            if (candidateDom != dom) {
                cursor = LocalDateTime.of(y, mo, candidateDom, 0, 0, 0);
                continue;
            }

            if (!hours.values.contains(h)) {
                Integer nh = hours.values.ceiling(h);
                if (nh == null) {
                    cursor = LocalDateTime.of(y, mo, dom, 0, 0, 0).plusDays(1);
                    continue;
                }
                cursor = LocalDateTime.of(y, mo, dom, nh, 0, 0);
                continue;
            }

            if (!minutes.values.contains(mi)) {
                Integer nm = minutes.values.ceiling(mi);
                if (nm == null) {
                    cursor = LocalDateTime.of(y, mo, dom, h, 0, 0).plusHours(1);
                    continue;
                }
                cursor = LocalDateTime.of(y, mo, dom, h, nm, 0);
                continue;
            }

            if (!seconds.values.contains(se)) {
                Integer ns = seconds.values.ceiling(se);
                if (ns == null) {
                    cursor = LocalDateTime.of(y, mo, dom, h, mi, 0).plusMinutes(1);
                    continue;
                }
                cursor = LocalDateTime.of(y, mo, dom, h, mi, ns);
                continue;
            }
            return cursor;
        }
        return null;
    }

    private ZonedDateTime resolveLocal(LocalDateTime local, ZoneId zone) {
        var rules = zone.getRules();
        var trans = rules.getTransition(local);
        if (trans == null) {
            return ZonedDateTime.of(local, zone);
        }
        if (trans.isGap()) {
            // Skip past the entire gap and restart the search from the first
            // local instant that exists post-transition.
            LocalDateTime postGap = trans.getDateTimeAfter();
            LocalDateTime nxt = findNext(postGap);
            if (nxt == null) return null;
            return resolveLocal(nxt, zone);
        }
        if (trans.isOverlap()) {
            return ZonedDateTime.ofLocal(local, zone, trans.getOffsetBefore());
        }
        return ZonedDateTime.of(local, zone);
    }

    private static FieldSpec parseSimple(String raw, CronFieldType type) {
        TreeSet<Integer> out = new TreeSet<>();
        String[] parts = raw.split(",");
        StringBuilder specials = new StringBuilder();
        for (String p : parts) {
            String t = p.trim();
            if (t.isEmpty()) throw new CronParseException("empty list element in " + type);
            if ("?".equals(t)) {
                if (type != CronFieldType.DAY_OF_MONTH && type != CronFieldType.DAY_OF_WEEK) {
                    throw new CronParseException("? not allowed in " + type);
                }
                specials.append("?");
                continue;
            }
            int step = 1;
            String range = t;
            int slash = t.indexOf('/');
            if (slash >= 0) {
                range = t.substring(0, slash);
                String stepStr = t.substring(slash + 1);
                try { step = Integer.parseInt(stepStr); }
                catch (NumberFormatException nfe) {
                    throw new CronParseException("invalid step in " + type + ": " + t);
                }
                if (step < 1) throw new CronParseException("step must be >= 1 in " + type);
                if (range.isEmpty() || "*".equals(range)) {
                    range = type.min + "-" + type.max;
                }
            }
            if ("*".equals(range)) {
                for (int v = type.min; v <= type.max; v += step) out.add(v);
                continue;
            }
            int dash = range.indexOf('-');
            int lo, hi;
            if (dash >= 0) {
                lo = parseValue(range.substring(0, dash), type);
                hi = parseValue(range.substring(dash + 1), type);
            } else {
                lo = parseValue(range, type);
                hi = lo;
            }
            if (lo < type.min || hi > type.max || lo > hi) {
                throw new CronParseException(type + " value out of range: " + t);
            }
            for (int v = lo; v <= hi; v += step) out.add(v);
        }
        if (out.isEmpty() && specials.length() == 0) {
            throw new CronParseException("no values for " + type + ": " + raw);
        }
        return new FieldSpec(out, specials.toString());
    }

    private static int parseValue(String s, CronFieldType type) {
        try { return Integer.parseInt(s); }
        catch (NumberFormatException nfe) {
            throw new CronParseException("invalid integer in " + type + ": " + s);
        }
    }

    private static String normalizeMonth(String raw) {
        String upper = raw.toUpperCase(Locale.ROOT);
        String[] names = {"JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"};
        for (int i = 0; i < names.length; i++) {
            upper = upper.replace(names[i], Integer.toString(i + 1));
        }
        return upper;
    }

    private static DomSpec parseDom(String raw) {
        if ("?".equals(raw)) return DomSpec.question();
        String upper = raw.toUpperCase(Locale.ROOT);
        if ("L".equals(upper)) return DomSpec.lastDay();
        if ("LW".equals(upper)) return DomSpec.lastWeekday();
        if (upper.endsWith("W") && upper.length() > 1 && !upper.contains(",") && !upper.contains("-")) {
            try {
                int d = Integer.parseInt(upper.substring(0, upper.length() - 1));
                if (d < 1 || d > 31) throw new CronParseException("dW value out of range: " + raw);
                return DomSpec.nearestWeekday(d);
            } catch (NumberFormatException nfe) {
                throw new CronParseException("invalid dW value: " + raw);
            }
        }
        FieldSpec fs = parseSimple(upper, CronFieldType.DAY_OF_MONTH);
        return DomSpec.fromValues(fs.values, fs.special);
    }

    private static DowSpec parseDow(String raw) {
        if ("?".equals(raw)) return DowSpec.question();
        String upper = raw.toUpperCase(Locale.ROOT);
        upper = normalizeDow(upper);
        if (upper.matches("[1-7]L")) {
            int dow = Integer.parseInt(upper.substring(0, 1));
            return DowSpec.lastInMonth(dow);
        }
        if (upper.equals("L")) {
            return DowSpec.lastInMonth(7);
        }
        if (upper.matches("[1-7]#[1-5]")) {
            int dow = Integer.parseInt(upper.substring(0, 1));
            int n = Integer.parseInt(upper.substring(2));
            return DowSpec.nthInMonth(dow, n);
        }
        FieldSpec fs = parseSimple(upper, CronFieldType.DAY_OF_WEEK);
        return DowSpec.fromValues(fs.values, fs.special);
    }

    private static String normalizeDow(String raw) {
        String[][] names = {
            {"SUN", "1"}, {"MON", "2"}, {"TUE", "3"}, {"WED", "4"},
            {"THU", "5"}, {"FRI", "6"}, {"SAT", "7"}
        };
        String upper = raw;
        for (String[] pair : names) upper = upper.replace(pair[0], pair[1]);
        return upper;
    }

    private static class FieldSpec {
        final TreeSet<Integer> values;
        final String special;
        FieldSpec(TreeSet<Integer> values, String special) {
            this.values = values;
            this.special = special;
        }
    }

    private static class DomSpec {
        final boolean question;
        final boolean lastDay;
        final boolean lastWeekday;
        final Integer nearestWeekday;
        final TreeSet<Integer> values;
        final String special;

        private DomSpec(boolean question, boolean lastDay, boolean lastWeekday,
                        Integer nearestWeekday, TreeSet<Integer> values, String special) {
            this.question = question;
            this.lastDay = lastDay;
            this.lastWeekday = lastWeekday;
            this.nearestWeekday = nearestWeekday;
            this.values = values;
            this.special = special;
        }

        static DomSpec question() { return new DomSpec(true, false, false, null, new TreeSet<>(), "?"); }
        static DomSpec lastDay() { return new DomSpec(false, true, false, null, new TreeSet<>(), "L"); }
        static DomSpec lastWeekday() { return new DomSpec(false, false, true, null, new TreeSet<>(), "LW"); }
        static DomSpec nearestWeekday(int d) {
            return new DomSpec(false, false, false, d, new TreeSet<>(), d + "W");
        }
        static DomSpec fromValues(TreeSet<Integer> v, String s) {
            return new DomSpec(false, false, false, null, v, s);
        }

        boolean isQuestion() { return question; }

        int firstDomOnOrAfter(int year, int month, int dom) {
            int last = YearMonth.of(year, month).lengthOfMonth();
            if (lastDay) {
                return dom <= last ? last : -1;
            }
            if (lastWeekday) {
                int d = lastWeekdayOfMonth(year, month);
                return dom <= d ? d : -1;
            }
            if (nearestWeekday != null) {
                int target = Math.min(nearestWeekday, last);
                int adj = nearestWeekdayInMonth(year, month, target);
                return dom <= adj ? adj : -1;
            }
            Integer cand = values.ceiling(dom);
            if (cand == null || cand > last) return -1;
            return cand;
        }

        private int lastWeekdayOfMonth(int year, int month) {
            int last = YearMonth.of(year, month).lengthOfMonth();
            LocalDate d = LocalDate.of(year, month, last);
            while (d.getDayOfWeek() == DayOfWeek.SATURDAY || d.getDayOfWeek() == DayOfWeek.SUNDAY) {
                d = d.minusDays(1);
            }
            return d.getDayOfMonth();
        }

        private int nearestWeekdayInMonth(int year, int month, int target) {
            int last = YearMonth.of(year, month).lengthOfMonth();
            LocalDate d = LocalDate.of(year, month, target);
            if (d.getDayOfWeek() == DayOfWeek.SATURDAY) {
                if (target == 1) {
                    LocalDate up = d;
                    while (up.getDayOfWeek() == DayOfWeek.SATURDAY || up.getDayOfWeek() == DayOfWeek.SUNDAY) {
                        up = up.plusDays(1);
                    }
                    return up.getDayOfMonth();
                }
                return d.minusDays(1).getDayOfMonth();
            }
            if (d.getDayOfWeek() == DayOfWeek.SUNDAY) {
                if (target == last) {
                    return d.minusDays(2).getDayOfMonth();
                }
                return d.plusDays(1).getDayOfMonth();
            }
            return target;
        }
    }

    private static class DowSpec {
        final boolean question;
        final Integer lastInMonthDow;
        final Integer nthDow;
        final Integer nthInMonth;
        final TreeSet<Integer> values;
        final String special;

        private DowSpec(boolean question, Integer lastInMonthDow, Integer nthDow, Integer nthInMonth,
                        TreeSet<Integer> values, String special) {
            this.question = question;
            this.lastInMonthDow = lastInMonthDow;
            this.nthDow = nthDow;
            this.nthInMonth = nthInMonth;
            this.values = values;
            this.special = special;
        }

        static DowSpec question() { return new DowSpec(true, null, null, null, new TreeSet<>(), "?"); }
        static DowSpec lastInMonth(int dow) { return new DowSpec(false, dow, null, null, new TreeSet<>(), dow + "L"); }
        static DowSpec nthInMonth(int dow, int n) { return new DowSpec(false, null, dow, n, new TreeSet<>(), dow + "#" + n); }
        static DowSpec fromValues(TreeSet<Integer> v, String s) { return new DowSpec(false, null, null, null, v, s); }

        int firstDomOnOrAfter(int year, int month, int dom) {
            int last = YearMonth.of(year, month).lengthOfMonth();
            if (lastInMonthDow != null) {
                int candidate = lastDowOfMonth(year, month, lastInMonthDow);
                return dom <= candidate ? candidate : -1;
            }
            if (nthDow != null) {
                int candidate = nthDowOfMonth(year, month, nthDow, nthInMonth);
                if (candidate < 0 || candidate > last) return -1;
                return dom <= candidate ? candidate : -1;
            }
            for (int d = dom; d <= last; d++) {
                int dow = quartzDow(LocalDate.of(year, month, d));
                if (values.contains(dow)) return d;
            }
            return -1;
        }

        private int lastDowOfMonth(int year, int month, int quartzDow) {
            int last = YearMonth.of(year, month).lengthOfMonth();
            for (int d = last; d >= 1; d--) {
                if (quartzDow(LocalDate.of(year, month, d)) == quartzDow) return d;
            }
            return -1;
        }

        private int nthDowOfMonth(int year, int month, int quartzDow, int n) {
            int last = YearMonth.of(year, month).lengthOfMonth();
            int found = 0;
            for (int d = 1; d <= last; d++) {
                if (quartzDow(LocalDate.of(year, month, d)) == quartzDow) {
                    found++;
                    if (found == n) return d;
                }
            }
            return -1;
        }

        private static int quartzDow(LocalDate d) {
            DayOfWeek dw = d.getDayOfWeek();
            switch (dw) {
                case SUNDAY: return 1;
                case MONDAY: return 2;
                case TUESDAY: return 3;
                case WEDNESDAY: return 4;
                case THURSDAY: return 5;
                case FRIDAY: return 6;
                case SATURDAY: return 7;
                default: throw new IllegalStateException();
            }
        }
    }
}
JAVA

mvn -B -q -DskipTests -o package
cp /app/target/chronos.jar /app/chronos.jar
echo "M1 oracle complete"
