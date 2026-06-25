package com.cronq;

import com.cronq.calc.NextCalculator;
import com.cronq.io.JsonWriter;
import com.cronq.model.CronExpr;
import com.cronq.parse.CronParser;
import com.cronq.parse.ParseException;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;

public final class Cli {

    private static final DateTimeFormatter ISO =
            DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss'Z'");

    public static void main(String[] args) {
        if (args.length == 0 || !args[0].equals("next")) {
            System.err.println("usage: cronq next --expr \"<5 fields>\" --from <iso8601> [--count N]");
            System.exit(2);
        }

        String expr = null;
        String from = null;
        int count = 5;

        int i = 1;
        while (i < args.length) {
            String a = args[i];
            switch (a) {
                case "--expr":
                    expr = need(args, ++i, "--expr");
                    break;
                case "--from":
                    from = need(args, ++i, "--from");
                    break;
                case "--count":
                    String cv = need(args, ++i, "--count");
                    try {
                        count = Integer.parseInt(cv);
                    } catch (NumberFormatException e) {
                        fail("--count must be an integer: '" + cv + "'");
                    }
                    break;
                default:
                    fail("unknown argument: '" + a + "'");
            }
            i++;
        }

        if (expr == null) {
            fail("missing --expr");
        }
        if (from == null) {
            fail("missing --from");
        }
        if (count < 1) {
            fail("--count must be >= 1");
        }

        CronExpr cron;
        try {
            cron = CronParser.parse(expr);
        } catch (ParseException e) {
            System.out.println(JsonWriter.error(e.getMessage()));
            System.exit(2);
            return;
        }

        Instant fromInstant;
        try {
            fromInstant = Instant.parse(from);
        } catch (DateTimeParseException e) {
            System.out.println(JsonWriter.error("bad --from timestamp: '" + from + "'"));
            System.exit(2);
            return;
        }

        List<LocalDateTime> hits = NextCalculator.next(cron, fromInstant, count);
        if (hits.size() < count) {
            System.out.println(JsonWriter.error(
                "could not find " + count + " future matches within the search horizon"));
            System.exit(3);
            return;
        }

        List<String> stamps = new ArrayList<>();
        for (LocalDateTime t : hits) {
            stamps.add(t.format(ISO));
        }
        System.out.println(JsonWriter.success(cron.raw, from, stamps));
        System.exit(0);
    }

    private static String need(String[] args, int idx, String flag) {
        if (idx >= args.length) {
            fail("missing value for " + flag);
        }
        return args[idx];
    }

    private static void fail(String msg) {
        System.out.println(JsonWriter.error(msg));
        System.exit(2);
    }

    private Cli() {
    }
}
