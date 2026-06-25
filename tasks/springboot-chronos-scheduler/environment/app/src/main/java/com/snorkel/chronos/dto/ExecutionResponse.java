package com.snorkel.chronos.dto;

import com.snorkel.chronos.domain.JobExecution;

public class ExecutionResponse {
    public Long id;
    public Long jobId;
    public String scheduledTime;
    public String status;
    public String startedAt;
    public String completedAt;
    public String errorMessage;
    public String lastHeartbeat;
    public String workerId;
    public int recoveryAttempt;

    public static ExecutionResponse from(JobExecution e) {
        ExecutionResponse r = new ExecutionResponse();
        r.id = e.getId();
        r.jobId = e.getJobId();
        r.scheduledTime = e.getScheduledTime() == null ? null : e.getScheduledTime().toString();
        r.status = e.getStatus() == null ? null : e.getStatus().name();
        r.startedAt = e.getStartedAt() == null ? null : e.getStartedAt().toString();
        r.completedAt = e.getCompletedAt() == null ? null : e.getCompletedAt().toString();
        r.errorMessage = e.getErrorMessage();
        r.lastHeartbeat = e.getLastHeartbeat() == null ? null : e.getLastHeartbeat().toString();
        r.workerId = e.getWorkerId();
        r.recoveryAttempt = e.getRecoveryAttempt();
        return r;
    }
}
