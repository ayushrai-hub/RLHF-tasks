package com.snorkel.chronos.job;

/**
 * Contract for a unit of scheduled work. The {@link JobContext} gives the bean
 * access to its execution id (for writing back log markers), the scheduled
 * time, and the recovery_attempt count for crash-recovered re-runs.
 */
public interface JobBean {
    /**
     * Run the unit of work. May throw — the dispatcher will mark the execution
     * FAILED and capture the message.
     */
    String execute(JobContext ctx) throws Exception;
}
