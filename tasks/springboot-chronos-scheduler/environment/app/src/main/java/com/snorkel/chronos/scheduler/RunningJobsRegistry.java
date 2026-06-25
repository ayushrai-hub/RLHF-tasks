package com.snorkel.chronos.scheduler;

import org.springframework.stereotype.Component;

import java.util.concurrent.ConcurrentHashMap;

/**
 * Tracks which worker thread is currently executing which executionId so the
 * verifier's simulate-crash hook can yank one. The agent's worker pool
 * registers a thread before invoking the JobBean and de-registers on completion.
 *
 * killAndDeregister interrupts the thread WITHOUT updating cron_executions —
 * leaving a stale CLAIMED/RUNNING row whose heartbeat will stop, which the
 * FailoverDetector must observe and recover.
 */
@Component
public class RunningJobsRegistry {

    private final ConcurrentHashMap<Long, Thread> running = new ConcurrentHashMap<>();

    public void register(long executionId, Thread t) {
        running.put(executionId, t);
    }

    public void deregister(long executionId) {
        running.remove(executionId);
    }

    public boolean killAndDeregister(long executionId) {
        Thread t = running.remove(executionId);
        if (t == null) return false;
        t.interrupt();
        return true;
    }

    public boolean isRunning(long executionId) {
        return running.containsKey(executionId);
    }

    public int size() { return running.size(); }
}
