package com.snorkel.chronos.domain;

import java.time.Instant;

public class JobExecution {
    private Long id;
    private Long jobId;
    private Instant scheduledTime;
    private ExecutionStatus status;
    private Instant startedAt;
    private Instant completedAt;
    private String errorMessage;
    private Instant lastHeartbeat;
    private String workerId;
    private int recoveryAttempt;

    public JobExecution() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getJobId() { return jobId; }
    public void setJobId(Long jobId) { this.jobId = jobId; }
    public Instant getScheduledTime() { return scheduledTime; }
    public void setScheduledTime(Instant scheduledTime) { this.scheduledTime = scheduledTime; }
    public ExecutionStatus getStatus() { return status; }
    public void setStatus(ExecutionStatus status) { this.status = status; }
    public Instant getStartedAt() { return startedAt; }
    public void setStartedAt(Instant startedAt) { this.startedAt = startedAt; }
    public Instant getCompletedAt() { return completedAt; }
    public void setCompletedAt(Instant completedAt) { this.completedAt = completedAt; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public Instant getLastHeartbeat() { return lastHeartbeat; }
    public void setLastHeartbeat(Instant lastHeartbeat) { this.lastHeartbeat = lastHeartbeat; }
    public String getWorkerId() { return workerId; }
    public void setWorkerId(String workerId) { this.workerId = workerId; }
    public int getRecoveryAttempt() { return recoveryAttempt; }
    public void setRecoveryAttempt(int recoveryAttempt) { this.recoveryAttempt = recoveryAttempt; }
}
