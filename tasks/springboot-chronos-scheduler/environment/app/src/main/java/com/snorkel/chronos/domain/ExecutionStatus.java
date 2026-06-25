package com.snorkel.chronos.domain;

public enum ExecutionStatus {
    PENDING,
    CLAIMED,
    RUNNING,
    SUCCEEDED,
    FAILED,
    SKIPPED,
    MISFIRED
}
