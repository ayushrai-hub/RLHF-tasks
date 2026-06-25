package com.snorkel.chronos.controller;

import com.snorkel.chronos.domain.ExecutionStatus;
import com.snorkel.chronos.domain.JobDefinition;
import com.snorkel.chronos.domain.JobExecution;
import com.snorkel.chronos.domain.JobState;
import com.snorkel.chronos.domain.MisfireInstruction;
import com.snorkel.chronos.dto.ExecutionResponse;
import com.snorkel.chronos.dto.JobCreateRequest;
import com.snorkel.chronos.dto.JobResponse;
import com.snorkel.chronos.exception.JobNotFoundException;
import com.snorkel.chronos.job.JobRegistry;
import com.snorkel.chronos.repository.ExecutionDao;
import com.snorkel.chronos.repository.JobDao;
import com.snorkel.chronos.scheduler.JobDispatcher;
import com.snorkel.chronos.scheduler.MisfireHandler;
import com.snorkel.chronos.cron.QuartzCronExpression;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/jobs")
public class JobController {

    private final JobDao jobDao;
    private final ExecutionDao execDao;
    private final JobRegistry registry;
    private final JobDispatcher dispatcher;
    private final MisfireHandler misfireHandler;
    private final Clock clock;

    public JobController(JobDao jobDao,
                         ExecutionDao execDao,
                         JobRegistry registry,
                         JobDispatcher dispatcher,
                         MisfireHandler misfireHandler,
                         Clock clock) {
        this.jobDao = jobDao;
        this.execDao = execDao;
        this.registry = registry;
        this.dispatcher = dispatcher;
        this.misfireHandler = misfireHandler;
        this.clock = clock;
    }

    @PostMapping
    public ResponseEntity<JobResponse> create(@RequestBody JobCreateRequest req) {
        if (req.name == null || req.name.isEmpty()) {
            throw new IllegalArgumentException("name is required");
        }
        if (req.jobClass == null || !registry.isKnown(req.jobClass)) {
            throw new IllegalArgumentException("unknown job_class: " + req.jobClass);
        }
        if (req.cronExpr == null || req.cronExpr.isEmpty()) {
            throw new IllegalArgumentException("cronExpr is required");
        }
        QuartzCronExpression expr = QuartzCronExpression.parse(req.cronExpr);
        ZoneId zone = (req.zone == null || req.zone.isEmpty()) ? ZoneId.of("UTC") : ZoneId.of(req.zone);
        MisfireInstruction mi = (req.misfire == null || req.misfire.isEmpty())
                ? MisfireInstruction.FIRE_NOW
                : MisfireInstruction.valueOf(req.misfire);

        JobDefinition def = new JobDefinition();
        def.setName(req.name);
        def.setJobClass(req.jobClass);
        def.setCronExpr(req.cronExpr);
        def.setZone(zone.getId());
        def.setMisfire(mi);
        def.setConcurrentExecutionDisallowed(req.concurrentExecutionDisallowed);
        def.setState(JobState.ACTIVE);
        ZonedDateTime now = clock.instant().atZone(zone);
        ZonedDateTime nxt = expr.nextExecutionTime(now);
        def.setNextFireTime(nxt == null ? null : nxt.toInstant());
        def.setCreatedAt(clock.instant());

        long id = jobDao.insert(def);
        def.setId(id);
        return ResponseEntity.ok(JobResponse.from(def));
    }

    @GetMapping("/{id}")
    public ResponseEntity<JobResponse> get(@PathVariable long id) {
        JobDefinition def = jobDao.findById(id)
                .orElseThrow(() -> new JobNotFoundException("job " + id + " not found"));
        JobResponse r = JobResponse.from(def);
        List<JobExecution> execs = execDao.findByJob(id, 10);
        r.executions = execs.stream().map(ExecutionResponse::from).collect(Collectors.toList());
        return ResponseEntity.ok(r);
    }

    @GetMapping("/{id}/executions")
    public List<ExecutionResponse> executions(@PathVariable long id,
                                              @RequestParam(defaultValue = "20") int limit) {
        // Verify job exists; surfaces a 404 ApiError if not.
        jobDao.findById(id).orElseThrow(() -> new JobNotFoundException("job " + id + " not found"));
        return execDao.findByJob(id, limit).stream()
                .map(ExecutionResponse::from)
                .collect(Collectors.toList());
    }

    @PostMapping("/{id}/pause")
    public ResponseEntity<JobResponse> pause(@PathVariable long id) {
        JobDefinition def = jobDao.findById(id)
                .orElseThrow(() -> new JobNotFoundException("job " + id + " not found"));
        jobDao.updateState(id, JobState.PAUSED);
        def.setState(JobState.PAUSED);
        return ResponseEntity.ok(JobResponse.from(def));
    }

    @PostMapping("/{id}/resume")
    public ResponseEntity<JobResponse> resume(@PathVariable long id) {
        JobDefinition def = jobDao.findById(id)
                .orElseThrow(() -> new JobNotFoundException("job " + id + " not found"));
        // Apply the misfire policy while the job is still PAUSED, then flip to ACTIVE.
        // The scheduler loop only scans state='ACTIVE' rows, so handling the missed fire
        // before the state flip closes the race where the loop and this handler both fire
        // the policy and write duplicate rows; by the time the job is ACTIVE its
        // next_fire_time has already been advanced past now.
        Instant now = clock.instant();
        misfireHandler.handleResume(def, now);
        jobDao.updateState(id, JobState.ACTIVE);
        def.setState(JobState.ACTIVE);
        return ResponseEntity.ok(JobResponse.from(def));
    }

    @PostMapping("/{id}/trigger-now")
    public ResponseEntity<ExecutionResponse> triggerNow(@PathVariable long id) {
        JobDefinition def = jobDao.findById(id)
                .orElseThrow(() -> new JobNotFoundException("job " + id + " not found"));
        long execId = execDao.insertPending(def.getId(), clock.instant(), 0);
        JobExecution e = execDao.findById(execId).orElseThrow();
        dispatcher.signalNewWork();
        return ResponseEntity.ok(ExecutionResponse.from(e));
    }
}
