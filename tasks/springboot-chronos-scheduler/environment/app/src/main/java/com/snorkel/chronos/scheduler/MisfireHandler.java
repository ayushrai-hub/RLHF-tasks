package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.cron.QuartzCronExpression;
import com.snorkel.chronos.domain.JobDefinition;
import com.snorkel.chronos.repository.ExecutionDao;
import com.snorkel.chronos.repository.JobDao;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;

/**
 * Implements the three misfire instructions:
 *   FIRE_NOW                       — insert an immediate execution row, advance next based on now
 *   DO_NOTHING                     — skip the missed fires, advance next based on cron from now
 *   FIRE_NEXT_WITH_REMAINING_COUNT — insert a single MISFIRED summary row, advance next from now
 *
 * A job is "misfired" when its state was ACTIVE but next_fire_time is older
 * than now - threshold (default 60s). Called both by the scheduler loop at
 * tick time and by resume to catch up after a pause.
 */
@Component
public class MisfireHandler {

    protected final JobDao jobDao;
    protected final ExecutionDao execDao;
    protected final SchedulerConfig cfg;
    protected final Clock clock;

    public MisfireHandler(JobDao jobDao, ExecutionDao execDao, SchedulerConfig cfg, Clock clock) {
        this.jobDao = jobDao;
        this.execDao = execDao;
        this.cfg = cfg;
        this.clock = clock;
    }

    public void handleResume(JobDefinition def, Instant now) {
        throw new UnsupportedOperationException("milestone 2: implement MisfireHandler.handleResume");
    }

    public boolean isMisfired(JobDefinition def, Instant now) {
        if (def.getNextFireTime() == null) return false;
        long delta = now.getEpochSecond() - def.getNextFireTime().getEpochSecond();
        return delta > cfg.getMisfire().getThresholdSeconds();
    }

    public Instant computeNextAfter(JobDefinition def, Instant after) {
        ZoneId zone = ZoneId.of(def.getZone());
        QuartzCronExpression expr = QuartzCronExpression.parse(def.getCronExpr());
        ZonedDateTime nxt = expr.nextExecutionTime(after.atZone(zone));
        return nxt == null ? null : nxt.toInstant();
    }
}
