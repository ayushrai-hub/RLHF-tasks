package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.repository.JobDao;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.springframework.stereotype.Component;

import java.time.Clock;

/**
 * Periodic poller that scans cron_jobs for ACTIVE entries whose
 * next_fire_time is at or before {@link Clock#instant()}, inserts a PENDING
 * cron_executions row for each, advances the job's next_fire_time, and signals
 * the dispatcher.
 *
 * Agent owns the loop body in milestone 2.
 */
@Component
public class SchedulerLoop {

    protected final JobDao jobDao;
    protected final JobDispatcher dispatcher;
    protected final MisfireHandler misfireHandler;
    protected final SchedulerConfig cfg;
    protected final Clock clock;
    protected volatile boolean running = false;
    protected Thread thread;

    public SchedulerLoop(JobDao jobDao,
                         JobDispatcher dispatcher,
                         MisfireHandler misfireHandler,
                         SchedulerConfig cfg,
                         Clock clock) {
        this.jobDao = jobDao;
        this.dispatcher = dispatcher;
        this.misfireHandler = misfireHandler;
        this.cfg = cfg;
        this.clock = clock;
    }

    @PostConstruct
    public void start() {
        running = true;
        thread = new Thread(this::loop, "chronos-scheduler-loop");
        thread.setDaemon(true);
        thread.start();
    }

    @PreDestroy
    public void stop() {
        running = false;
        if (thread != null) thread.interrupt();
    }

    protected void loop() {
        while (running) {
            try {
                tick();
            } catch (Throwable t) {
                // swallow; keep looping
            }
            try {
                Thread.sleep(cfg.getScheduler().getPollIntervalMs());
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }

    protected void tick() {
        throw new UnsupportedOperationException("milestone 2: implement SchedulerLoop.tick");
    }
}
