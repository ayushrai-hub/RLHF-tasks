package com.cronq.parse;

import com.cronq.model.Field;

import java.util.Map;
import java.util.TreeSet;

public final class FieldParser {

    public static Field parse(String spec, int min, int max,
                              Map<String, Integer> names) throws ParseException {
        if (spec == null || spec.isEmpty()) {
            throw new ParseException("empty field");
        }
        TreeSet<Integer> out = new TreeSet<>();
        for (String item : spec.split(",", -1)) {
            parseItem(item, min, max, names, out);
        }
        boolean restricted = !spec.startsWith("*");
        return new Field(out, restricted, spec);
    }

    private static void parseItem(String item, int min, int max,
                                  Map<String, Integer> names, TreeSet<Integer> out)
            throws ParseException {
        if (item.isEmpty()) {
            throw new ParseException("empty term in field");
        }

        int step = 1;
        String base = item;
        int slash = item.indexOf('/');
        if (slash >= 0) {
            base = item.substring(0, slash);
            String stepStr = item.substring(slash + 1);
            try {
                step = Integer.parseInt(stepStr);
            } catch (NumberFormatException e) {
                throw new ParseException("bad step '" + stepStr + "' in '" + item + "'");
            }
            if (step < 1) {
                throw new ParseException("step must be >= 1 in '" + item + "'");
            }
        }

        int lo;
        int hi;
        if (base.equals("*")) {
            lo = min;
            hi = max;
        } else if (base.indexOf('-') > 0) {
            int dash = base.indexOf('-');
            lo = value(base.substring(0, dash), names);
            hi = (slash >= 0) ? max : value(base.substring(dash + 1), names);
        } else {
            int v = value(base, names);
            lo = (slash >= 0) ? min : v;
            hi = (slash >= 0) ? max : v;
        }

        if (lo < min || hi > max || lo > hi) {
            throw new ParseException(
                "value out of range in '" + item + "' (allowed " + min + "-" + max + ")");
        }
        for (int x = lo; x <= hi; x += step) {
            out.add(x);
        }
    }

    private static int value(String token, Map<String, Integer> names) throws ParseException {
        try {
            return Integer.parseInt(token);
        } catch (NumberFormatException ignored) {
            // not a plain number, try the name table below
        }
        if (names != null) {
            Integer n = names.get(token.toUpperCase());
            if (n != null) {
                return n;
            }
        }
        throw new ParseException("not a number or known name: '" + token + "'");
    }

    private FieldParser() {
    }
}
