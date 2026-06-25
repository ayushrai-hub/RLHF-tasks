package com.cronq.match;

import com.cronq.model.CronExpr;

import java.time.LocalDateTime;

public final class Matcher {

    public static boolean dayMatches(CronExpr expr, LocalDateTime t) {
        boolean domRestricted = expr.dayOfMonth.isRestricted();
        boolean dowRestricted = expr.dayOfWeek.isRestricted();

        boolean domOk = expr.dayOfMonth.allows(t.getDayOfMonth());
        int cronDow = t.getDayOfWeek().getValue();
        boolean dowOk = expr.dayOfWeek.allows(cronDow);

        if (domRestricted && dowRestricted) {
            return domOk && dowOk;
        }
        if (domRestricted) {
            return domOk;
        }
        if (dowRestricted) {
            return dowOk;
        }
        return true;
    }

    private Matcher() {
    }
}
