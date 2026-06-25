package com.snorkel.chronos.domain;

import java.time.Instant;

public class JobDefinition {
    private Long id;
    private String name;
    private String jobClass;
    private String cronExpr;
    private String zone;
    private MisfireInstruction misfire;
    private boolean concurrentExecutionDisallowed;
    private JobState state;
    private Instant nextFireTime;
    private Instant createdAt;

    public JobDefinition() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getJobClass() { return jobClass; }
    public void setJobClass(String jobClass) { this.jobClass = jobClass; }
    public String getCronExpr() { return cronExpr; }
    public void setCronExpr(String cronExpr) { this.cronExpr = cronExpr; }
    public String getZone() { return zone; }
    public void setZone(String zone) { this.zone = zone; }
    public MisfireInstruction getMisfire() { return misfire; }
    public void setMisfire(MisfireInstruction misfire) { this.misfire = misfire; }
    public boolean isConcurrentExecutionDisallowed() { return concurrentExecutionDisallowed; }
    public void setConcurrentExecutionDisallowed(boolean v) { this.concurrentExecutionDisallowed = v; }
    public JobState getState() { return state; }
    public void setState(JobState state) { this.state = state; }
    public Instant getNextFireTime() { return nextFireTime; }
    public void setNextFireTime(Instant nextFireTime) { this.nextFireTime = nextFireTime; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
