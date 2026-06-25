package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.repository.ExecutionDao;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.springframework.stereotype.Component;

import java.time.Clock;

/**
 * Scans for cron_executions whose status is CLAIMED or RUNNING but whose
 * last_heartbeat is older than chronos.heartbeat.timeoutMs. Marks the stale
 * row FAILED with error_message='worker_lost_heartbeat' and inserts a new
 * PENDING row at the same scheduled_time with recovery_attempt + 1 (capped at
 * chronos.heartbeat.maxRecoveryAttempts).
 *
 * Agent owns the detector body in milestone 3.
 */
@Component
public class FailoverDetector {

    protected final ExecutionDao execDao;
    protected final SchedulerConfig cfg;
    protected final Clock clock;
    protected volatile boolean running = false;
    protected Thread thread;

    public FailoverDetector(ExecutionDao execDao, SchedulerConfig cfg, Clock clock) {
        this.execDao = execDao;
        this.cfg = cfg;
        this.clock = clock;
    }

    @PostConstruct
    public void start() {
        running = true;
        thread = new Thread(this::loop, "chronos-failover");
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
                Thread.sleep(5_000L);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }

    protected void tick() {
        throw new UnsupportedOperationException("milestone 3: implement FailoverDetector.tick");
    }
}
