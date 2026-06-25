package com.cronq.model;

public final class CronExpr {
    public final Field minute;
    public final Field hour;
    public final Field dayOfMonth;
    public final Field month;
    public final Field dayOfWeek;
    public final String raw;

    public CronExpr(Field minute, Field hour, Field dayOfMonth,
                    Field month, Field dayOfWeek, String raw) {
        this.minute = minute;
        this.hour = hour;
        this.dayOfMonth = dayOfMonth;
        this.month = month;
        this.dayOfWeek = dayOfWeek;
        this.raw = raw;
    }
}
