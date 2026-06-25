package com.snorkel.chronos.dto;

public class JobCreateRequest {
    public String name;
    public String jobClass;
    public String cronExpr;
    public String zone;
    public String misfire;
    public boolean concurrentExecutionDisallowed;
}
