package com.snorkel.chronos.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConfigurationProperties(prefix = "chronos")
public class SchedulerConfig {

    private int workers = 4;
    private Scheduler scheduler = new Scheduler();
    private Heartbeat heartbeat = new Heartbeat();
    private Misfire misfire = new Misfire();

    public int getWorkers() { return workers; }
    public void setWorkers(int workers) { this.workers = workers; }
    public Scheduler getScheduler() { return scheduler; }
    public void setScheduler(Scheduler s) { this.scheduler = s; }
    public Heartbeat getHeartbeat() { return heartbeat; }
    public void setHeartbeat(Heartbeat h) { this.heartbeat = h; }
    public Misfire getMisfire() { return misfire; }
    public void setMisfire(Misfire m) { this.misfire = m; }

    public static class Scheduler {
        private long pollIntervalMs = 1000;
        public long getPollIntervalMs() { return pollIntervalMs; }
        public void setPollIntervalMs(long v) { this.pollIntervalMs = v; }
    }

    public static class Heartbeat {
        private long intervalMs = 1000;
        private long timeoutMs = 10000;
        private int maxRecoveryAttempts = 3;
        public long getIntervalMs() { return intervalMs; }
        public void setIntervalMs(long v) { this.intervalMs = v; }
        public long getTimeoutMs() { return timeoutMs; }
        public void setTimeoutMs(long v) { this.timeoutMs = v; }
        public int getMaxRecoveryAttempts() { return maxRecoveryAttempts; }
        public void setMaxRecoveryAttempts(int v) { this.maxRecoveryAttempts = v; }
    }

    public static class Misfire {
        private long thresholdSeconds = 60;
        public long getThresholdSeconds() { return thresholdSeconds; }
        public void setThresholdSeconds(long v) { this.thresholdSeconds = v; }
    }
}
