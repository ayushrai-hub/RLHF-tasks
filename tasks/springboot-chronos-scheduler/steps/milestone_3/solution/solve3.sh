#!/usr/bin/env bash
# Oracle for milestone 3 — multi-worker dispatcher with atomic claim,
# concurrent_execution_disallowed, heartbeats, failover detection.
# Self-contained — re-writes M2's DAO + dispatcher + scheduler + misfire from scratch too.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Pull in M1 and M2 solutions first so this script is self-contained.
if [ -f "$SCRIPT_DIR/../../milestone_1/solution/solve1.sh" ]; then
  bash "$SCRIPT_DIR/../../milestone_1/solution/solve1.sh" >/dev/null
fi
if [ -f "$SCRIPT_DIR/../../milestone_2/solution/solve2.sh" ]; then
  bash "$SCRIPT_DIR/../../milestone_2/solution/solve2.sh" >/dev/null
fi

cd /app

# ---------- HeartbeatRegistrar.java (full DB writes) ----------
cat > /app/src/main/java/com/snorkel/chronos/scheduler/HeartbeatRegistrar.java <<'JAVA'
package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.repository.ExecutionDao;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class HeartbeatRegistrar {

    private static final Logger LOG = LoggerFactory.getLogger(HeartbeatRegistrar.class);

    protected final ExecutionDao execDao;
    protected final SchedulerConfig cfg;
    protected final Clock clock;
    protected final Map<Long, Boolean> tracked = new ConcurrentHashMap<>();
    protected volatile boolean running = false;
    protected Thread thread;

    public HeartbeatRegistrar(ExecutionDao execDao, SchedulerConfig cfg, Clock clock) {
        this.execDao = execDao;
        this.cfg = cfg;
        this.clock = clock;
    }

    @PostConstruct
    public void start() {
        running = true;
        thread = new Thread(this::loop, "chronos-heartbeat");
        thread.setDaemon(true);
        thread.start();
    }

    @PreDestroy
    public void stop() {
        running = false;
        if (thread != null) thread.interrupt();
    }

    public void track(long executionId) { tracked.put(executionId, Boolean.TRUE); }
    public void untrack(long executionId) { tracked.remove(executionId); }

    protected void loop() {
        while (running) {
            try { tick(); } catch (Throwable t) { LOG.debug("hb tick error", t); }
            try { Thread.sleep(cfg.getHeartbeat().getIntervalMs()); }
            catch (InterruptedException ie) { Thread.currentThread().interrupt(); return; }
        }
    }

    protected void tick() {
        Set<Long> snap = new HashSet<>(tracked.keySet());
        for (Long id : snap) {
            execDao.updateHeartbeat(id, clock.instant());
        }
    }
}
JAVA

# ---------- FailoverDetector.java (real failover logic) ----------
cat > /app/src/main/java/com/snorkel/chronos/scheduler/FailoverDetector.java <<'JAVA'
package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.domain.ExecutionStatus;
import com.snorkel.chronos.domain.JobExecution;
import com.snorkel.chronos.repository.ExecutionDao;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;

@Component
public class FailoverDetector {

    private static final Logger LOG = LoggerFactory.getLogger(FailoverDetector.class);

    protected final ExecutionDao execDao;
    protected final SchedulerConfig cfg;
    protected final Clock clock;
    protected final JobDispatcher dispatcher;
    protected volatile boolean running = false;
    protected Thread thread;

    public FailoverDetector(ExecutionDao execDao, SchedulerConfig cfg, Clock clock, JobDispatcher dispatcher) {
        this.execDao = execDao;
        this.cfg = cfg;
        this.clock = clock;
        this.dispatcher = dispatcher;
    }

    @PostConstruct
    public void start() {
        running = true;
        thread = new Thread(this::loop, "chronos-failover");
        thread.setDaemon(true);
        thread.start();
    }

    @PreDestroy
    public void stop() {
        running = false;
        if (thread != null) thread.interrupt();
    }

    protected void loop() {
        while (running) {
            try { tick(); } catch (Throwable t) { LOG.debug("fo tick error", t); }
            try { Thread.sleep(2_500L); }
            catch (InterruptedException ie) { Thread.currentThread().interrupt(); return; }
        }
    }

    protected void tick() {
        Instant cutoff = clock.instant().minus(Duration.ofMillis(cfg.getHeartbeat().getTimeoutMs()));
        List<JobExecution> stale = execDao.findStaleClaimed(cutoff);
        for (JobExecution e : stale) {
            execDao.markCompleted(e.getId(), ExecutionStatus.FAILED, clock.instant(), "worker_lost_heartbeat");
            int nextAttempt = e.getRecoveryAttempt() + 1;
            if (nextAttempt <= cfg.getHeartbeat().getMaxRecoveryAttempts()) {
                execDao.insertPending(e.getJobId(), e.getScheduledTime(), nextAttempt);
                dispatcher.signalNewWork();
            }
        }
    }
}
JAVA

# ---------- JobDispatcher.java (full N-worker + concurrent_execution_disallowed) ----------
cat > /app/src/main/java/com/snorkel/chronos/scheduler/JobDispatcher.java <<'JAVA'
package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.domain.ExecutionStatus;
import com.snorkel.chronos.domain.JobExecution;
import com.snorkel.chronos.job.JobBean;
import com.snorkel.chronos.job.JobContext;
import com.snorkel.chronos.job.JobRegistry;
import com.snorkel.chronos.repository.ExecutionDao;
import com.snorkel.chronos.repository.JobDao;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

@Component
public class JobDispatcher {

    private static final Logger LOG = LoggerFactory.getLogger(JobDispatcher.class);

    protected final JobDao jobDao;
    protected final ExecutionDao execDao;
    protected final JobRegistry registry;
    protected final RunningJobsRegistry runningJobs;
    protected final HeartbeatRegistrar heartbeats;
    protected final SchedulerConfig cfg;
    protected final Clock clock;

    protected final List<Thread> workers = new ArrayList<>();
    protected volatile boolean running = false;
    protected final Semaphore signal = new Semaphore(0);

    public JobDispatcher(JobDao jobDao, ExecutionDao execDao, JobRegistry registry,
                         RunningJobsRegistry runningJobs, HeartbeatRegistrar heartbeats,
                         SchedulerConfig cfg, Clock clock) {
        this.jobDao = jobDao;
        this.execDao = execDao;
        this.registry = registry;
        this.runningJobs = runningJobs;
        this.heartbeats = heartbeats;
        this.cfg = cfg;
        this.clock = clock;
    }

    @PostConstruct
    public void start() {
        running = true;
        int n = Math.max(1, cfg.getWorkers());
        for (int i = 0; i < n; i++) {
            final String workerId = "worker-" + i;
            Thread t = new Thread(() -> workerLoop(workerId), "chronos-" + workerId);
            t.setDaemon(true);
            t.start();
            workers.add(t);
        }
    }

    @PreDestroy
    public void stop() {
        running = false;
        signal.release(workers.size());
        for (Thread t : workers) t.interrupt();
    }

    public void signalNewWork() { signal.release(); }

    protected void workerLoop(String workerId) {
        while (running) {
            try {
                Optional<Long> claimed = execDao.claimNextPending(workerId, clock.instant());
                if (claimed.isEmpty()) {
                    signal.tryAcquire(500, TimeUnit.MILLISECONDS);
                    continue;
                }
                runOne(workerId, claimed.get());
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                return;
            } catch (Throwable t) {
                LOG.warn("worker loop error", t);
            }
        }
    }

    protected void runOne(String workerId, long execId) {
        Optional<JobExecution> exo = execDao.findById(execId);
        if (exo.isEmpty()) return;
        JobExecution e = exo.get();
        var job = jobDao.findById(e.getJobId()).orElse(null);
        if (job == null) {
            execDao.markCompleted(execId, ExecutionStatus.FAILED, clock.instant(), "job_definition_missing");
            return;
        }
        // concurrent_execution_disallowed check: if another execution is in
        // RUNNING or CLAIMED for the same job AND this one isn't itself the one
        // that flipped to RUNNING, mark SKIPPED.
        if (job.isConcurrentExecutionDisallowed()) {
            // Already CLAIMED (this exec) — count anyone ELSE that is CLAIMED/RUNNING.
            int active = execDao.countActiveExcluding(job.getId(), execId);
            if (active > 0) {
                execDao.markCompleted(execId, ExecutionStatus.SKIPPED, clock.instant(),
                        "concurrent_execution_disallowed");
                return;
            }
        }
        execDao.markStarted(execId, workerId, clock.instant());
        runningJobs.register(execId, Thread.currentThread());
        heartbeats.track(execId);
        try {
            JobBean bean = registry.lookup(job.getJobClass());
            String result = bean.execute(new JobContext(execId, job.getId(), e.getScheduledTime(), e.getRecoveryAttempt()));
            execDao.markCompleted(execId, ExecutionStatus.SUCCEEDED, clock.instant(), result);
        } catch (InterruptedException ie) {
            // Thread was killed (e.g. simulate-crash). Do NOT update the row — that
            // lets the FailoverDetector recover us via stale-heartbeat detection.
            // Clear the interrupt status (catching InterruptedException already does this
            // implicitly, but be defensive) so the worker can resume picking up new work
            // after the finally block runs. Re-asserting the flag here would kill the
            // worker thread on the next signal.tryAcquire call in workerLoop.
            Thread.interrupted();
        } catch (Throwable t) {
            execDao.markCompleted(execId, ExecutionStatus.FAILED, clock.instant(), shortError(t));
        } finally {
            heartbeats.untrack(execId);
            runningJobs.deregister(execId);
        }
    }

    private static String shortError(Throwable t) {
        String msg = t.getMessage();
        return (t.getClass().getSimpleName() + ": " + (msg == null ? "" : msg));
    }
}
JAVA

# ---------- ExecutionDao.java (add countActiveExcluding + ensure claim is atomic) ----------
cat > /app/src/main/java/com/snorkel/chronos/repository/ExecutionDao.java <<'JAVA'
package com.snorkel.chronos.repository;

import com.snorkel.chronos.domain.ExecutionStatus;
import com.snorkel.chronos.domain.JobExecution;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public class ExecutionDao {

    private final JdbcTemplate jdbc;

    public ExecutionDao(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    protected JdbcTemplate jdbc() { return jdbc; }

    private static final RowMapper<JobExecution> MAPPER = (rs, i) -> {
        JobExecution e = new JobExecution();
        e.setId(rs.getLong("id"));
        e.setJobId(rs.getLong("job_id"));
        Timestamp st = rs.getTimestamp("scheduled_time");
        e.setScheduledTime(st == null ? null : st.toInstant());
        e.setStatus(ExecutionStatus.valueOf(rs.getString("status")));
        Timestamp sa = rs.getTimestamp("started_at");
        e.setStartedAt(sa == null ? null : sa.toInstant());
        Timestamp ca = rs.getTimestamp("completed_at");
        e.setCompletedAt(ca == null ? null : ca.toInstant());
        e.setErrorMessage(rs.getString("error_message"));
        Timestamp lh = rs.getTimestamp("last_heartbeat");
        e.setLastHeartbeat(lh == null ? null : lh.toInstant());
        e.setWorkerId(rs.getString("worker_id"));
        e.setRecoveryAttempt(rs.getInt("recovery_attempt"));
        return e;
    };

    public long insertPending(long jobId, Instant scheduledTime, int recoveryAttempt) {
        KeyHolder kh = new GeneratedKeyHolder();
        jdbc.update(c -> {
            PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO cron_executions (job_id, scheduled_time, status, recovery_attempt) " +
                            "VALUES (?, ?, 'PENDING', ?)",
                    new String[]{"id"});
            ps.setLong(1, jobId);
            ps.setTimestamp(2, Timestamp.from(scheduledTime));
            ps.setInt(3, recoveryAttempt);
            return ps;
        }, kh);
        return kh.getKey().longValue();
    }

    public long insertMisfiredSummary(long jobId, Instant scheduledTime) {
        KeyHolder kh = new GeneratedKeyHolder();
        jdbc.update(c -> {
            PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO cron_executions (job_id, scheduled_time, status, error_message, completed_at) " +
                            "VALUES (?, ?, 'MISFIRED', 'misfire_summary', ?)",
                    new String[]{"id"});
            ps.setLong(1, jobId);
            ps.setTimestamp(2, Timestamp.from(scheduledTime));
            ps.setTimestamp(3, Timestamp.from(Instant.now()));
            return ps;
        }, kh);
        return kh.getKey().longValue();
    }

    public Optional<JobExecution> findById(long id) {
        try {
            return Optional.ofNullable(jdbc.queryForObject("SELECT * FROM cron_executions WHERE id = ?", MAPPER, id));
        } catch (EmptyResultDataAccessException e) {
            return Optional.empty();
        }
    }

    public List<JobExecution> findByJob(long jobId, int limit) {
        return jdbc.query(
                "SELECT * FROM cron_executions WHERE job_id = ? ORDER BY scheduled_time DESC, id DESC LIMIT ?",
                MAPPER, jobId, limit);
    }

    public void markStatus(long execId, ExecutionStatus status, String errorMessage) {
        jdbc.update(
                "UPDATE cron_executions SET status = ?, error_message = ?, completed_at = ? WHERE id = ?",
                status.name(), errorMessage, Timestamp.from(Instant.now()), execId);
    }

    public void markStarted(long execId, String workerId, Instant startedAt) {
        jdbc.update(
                "UPDATE cron_executions SET status = 'RUNNING', worker_id = ?, started_at = ?, last_heartbeat = ? " +
                        "WHERE id = ?",
                workerId, Timestamp.from(startedAt), Timestamp.from(startedAt), execId);
    }

    public void markCompleted(long execId, ExecutionStatus status, Instant completedAt, String errorMessage) {
        jdbc.update(
                "UPDATE cron_executions SET status = ?, completed_at = ?, error_message = ? WHERE id = ?",
                status.name(), Timestamp.from(completedAt), errorMessage, execId);
    }

    public void updateHeartbeat(long execId, Instant ts) {
        jdbc.update("UPDATE cron_executions SET last_heartbeat = ? WHERE id = ? AND status IN ('CLAIMED','RUNNING')",
                Timestamp.from(ts), execId);
    }

    public Optional<Long> claimNextPending(String workerId, Instant now) {
        // Atomic claim — single UPDATE returning the affected id.
        List<Long> candidates = jdbc.queryForList(
                "SELECT id FROM cron_executions WHERE status = 'PENDING' ORDER BY scheduled_time ASC, id ASC LIMIT 16",
                Long.class);
        for (Long id : candidates) {
            int updated = jdbc.update(
                    "UPDATE cron_executions SET status = 'CLAIMED', worker_id = ?, last_heartbeat = ? " +
                            "WHERE id = ? AND status = 'PENDING'",
                    workerId, Timestamp.from(now), id);
            if (updated == 1) return Optional.of(id);
        }
        return Optional.empty();
    }

    public int countActiveForJob(long jobId) {
        Integer n = jdbc.queryForObject(
                "SELECT COUNT(*) FROM cron_executions WHERE job_id = ? AND status IN ('CLAIMED','RUNNING')",
                Integer.class, jobId);
        return n == null ? 0 : n;
    }

    public int countActiveExcluding(long jobId, long excludeExecId) {
        Integer n = jdbc.queryForObject(
                "SELECT COUNT(*) FROM cron_executions WHERE job_id = ? AND status IN ('CLAIMED','RUNNING') AND id <> ?",
                Integer.class, jobId, excludeExecId);
        return n == null ? 0 : n;
    }

    public List<JobExecution> findStaleClaimed(Instant heartbeatBefore) {
        return jdbc.query(
                "SELECT * FROM cron_executions WHERE status IN ('CLAIMED','RUNNING') AND last_heartbeat IS NOT NULL " +
                        "AND last_heartbeat < ?",
                MAPPER, Timestamp.from(heartbeatBefore));
    }
}
JAVA

mvn -B -q -DskipTests -o package
cp /app/target/chronos.jar /app/chronos.jar
echo "M3 oracle complete"
