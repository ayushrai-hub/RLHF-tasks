package com.snorkel.chronos.dto;

import com.snorkel.chronos.domain.JobDefinition;

import java.util.List;

public class JobResponse {
    public Long id;
    public String name;
    public String jobClass;
    public String cronExpr;
    public String zone;
    public String misfire;
    public boolean concurrentExecutionDisallowed;
    public String state;
    public String nextFireTime;
    public String createdAt;
    public List<ExecutionResponse> executions;

    public static JobResponse from(JobDefinition d) {
        JobResponse r = new JobResponse();
        r.id = d.getId();
        r.name = d.getName();
        r.jobClass = d.getJobClass();
        r.cronExpr = d.getCronExpr();
        r.zone = d.getZone();
        r.misfire = d.getMisfire() == null ? null : d.getMisfire().name();
        r.concurrentExecutionDisallowed = d.isConcurrentExecutionDisallowed();
        r.state = d.getState() == null ? null : d.getState().name();
        r.nextFireTime = d.getNextFireTime() == null ? null : d.getNextFireTime().toString();
        r.createdAt = d.getCreatedAt() == null ? null : d.getCreatedAt().toString();
        return r;
    }
}
