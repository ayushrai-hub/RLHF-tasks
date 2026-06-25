package com.snorkel.chronos.job;

import java.time.Instant;

public class JobContext {
    private final long executionId;
    private final long jobId;
    private final Instant scheduledTime;
    private final int recoveryAttempt;

    public JobContext(long executionId, long jobId, Instant scheduledTime, int recoveryAttempt) {
        this.executionId = executionId;
        this.jobId = jobId;
        this.scheduledTime = scheduledTime;
        this.recoveryAttempt = recoveryAttempt;
    }

    public long getExecutionId() { return executionId; }
    public long getJobId() { return jobId; }
    public Instant getScheduledTime() { return scheduledTime; }
    public int getRecoveryAttempt() { return recoveryAttempt; }
}
