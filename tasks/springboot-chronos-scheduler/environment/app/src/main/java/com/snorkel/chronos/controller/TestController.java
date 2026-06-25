package com.snorkel.chronos.controller;

import com.snorkel.chronos.config.ClockConfig;
import com.snorkel.chronos.scheduler.RunningJobsRegistry;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * Verifier-only test hooks. Mutates the TestClock to drive misfire scenarios
 * deterministically and lets the verifier yank a running execution to drive
 * heartbeat-loss recovery tests.
 *
 * Not part of the production API surface — present so verifier tests have a
 * deterministic handle on time and process death.
 */
@RestController
@RequestMapping("/api/_test")
public class TestController {

    private final ClockConfig.TestClock clock;
    private final RunningJobsRegistry runningJobs;

    public TestController(ClockConfig.TestClock clock, RunningJobsRegistry runningJobs) {
        this.clock = clock;
        this.runningJobs = runningJobs;
    }

    @PostMapping("/advance-clock")
    public Map<String, Object> advanceClock(@RequestParam long seconds) {
        clock.advance(Duration.ofSeconds(seconds));
        Map<String, Object> out = new HashMap<>();
        out.put("offset_seconds", clock.getOffset().getSeconds());
        out.put("now", clock.instant().toString());
        return out;
    }

    @PostMapping("/reset-clock")
    public Map<String, Object> resetClock() {
        clock.reset();
        Map<String, Object> out = new HashMap<>();
        out.put("offset_seconds", 0);
        out.put("now", clock.instant().toString());
        return out;
    }

    @PostMapping("/simulate-crash/{executionId}")
    public Map<String, Object> simulateCrash(@PathVariable long executionId) {
        boolean killed = runningJobs.killAndDeregister(executionId);
        Map<String, Object> out = new HashMap<>();
        out.put("execution_id", executionId);
        out.put("killed", killed);
        return out;
    }
}
