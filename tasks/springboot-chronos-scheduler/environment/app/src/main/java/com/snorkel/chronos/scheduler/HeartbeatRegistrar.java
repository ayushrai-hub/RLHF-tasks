package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.repository.ExecutionDao;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;

/**
 * Background thread that periodically updates cron_executions.last_heartbeat
 * for every currently-running execution. When a worker thread is killed mid-job
 * (via simulate-crash), it's removed from this registry — its heartbeat goes
 * stale and FailoverDetector reclaims it.
 *
 * Agent owns the heartbeat tick body in milestone 3.
 */
@Component
public class HeartbeatRegistrar {

    protected final ExecutionDao execDao;
    protected final SchedulerConfig cfg;
    protected final Clock clock;
    protected final Map<Long, Boolean> tracked = new ConcurrentHashMap<>();
    protected volatile boolean running = false;
    protected Thread thread;

    public HeartbeatRegistrar(ExecutionDao execDao, SchedulerConfig cfg, Clock clock) {
        this.execDao = execDao;
        this.cfg = cfg;
        this.clock = clock;
    }

    @PostConstruct
    public void start() {
        running = true;
        thread = new Thread(this::loop, "chronos-heartbeat");
        thread.setDaemon(true);
        thread.start();
    }

    @PreDestroy
    public void stop() {
        running = false;
        if (thread != null) thread.interrupt();
    }

    public void track(long executionId) {
        tracked.put(executionId, Boolean.TRUE);
    }

    public void untrack(long executionId) {
        tracked.remove(executionId);
    }

    protected void loop() {
        while (running) {
            try {
                tick();
            } catch (Throwable t) {
                // swallow; keep looping
            }
            try {
                Thread.sleep(cfg.getHeartbeat().getIntervalMs());
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }

    protected void tick() {
        throw new UnsupportedOperationException("milestone 3: implement HeartbeatRegistrar.tick");
    }
}
