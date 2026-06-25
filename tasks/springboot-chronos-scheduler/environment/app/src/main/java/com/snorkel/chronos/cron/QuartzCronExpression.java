package com.snorkel.chronos.cron;

import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;

/**
 * Quartz-dialect 6-field cron expression: seconds minutes hours dayOfMonth month dayOfWeek.
 *
 * Agent owns the parse + nextExecutionTime implementation. Public surface is
 * fixed so the controller layer compiles regardless of internal representation.
 */
public class QuartzCronExpression {

    private final String expression;
    private final List<CronField> fields;

    private QuartzCronExpression(String expression, List<CronField> fields) {
        this.expression = expression;
        this.fields = fields;
    }

    public String getExpression() { return expression; }
    public List<CronField> getFields() { return fields; }

    public static QuartzCronExpression parse(String expression) {
        throw new UnsupportedOperationException("milestone 1: implement Quartz-dialect cron parser");
    }

    public ZonedDateTime nextExecutionTime(ZonedDateTime from) {
        throw new UnsupportedOperationException("milestone 1: implement nextExecutionTime");
    }

    public ZonedDateTime nextExecutionTime(ZonedDateTime from, ZoneId zone) {
        return nextExecutionTime(from.withZoneSameInstant(zone));
    }
}
