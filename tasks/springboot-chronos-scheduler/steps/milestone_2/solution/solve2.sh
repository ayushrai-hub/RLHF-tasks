#!/usr/bin/env bash
# Oracle for milestone 2 — JobDao + ExecutionDao + SchedulerLoop + JobDispatcher
# (single-threaded) + MisfireHandler. Self-contained.
set -euo pipefail

cd /app

# Re-write M1's parser too so M2 oracle works standalone if run without M1's solution mount.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../../milestone_1/solution/solve1.sh" ]; then
  bash "$SCRIPT_DIR/../../milestone_1/solution/solve1.sh" >/dev/null
fi

# ---------- JobDao.java ----------
cat > /app/src/main/java/com/snorkel/chronos/repository/JobDao.java <<'JAVA'
package com.snorkel.chronos.repository;

import com.snorkel.chronos.domain.JobDefinition;
import com.snorkel.chronos.domain.JobState;
import com.snorkel.chronos.domain.MisfireInstruction;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public class JobDao {

    private final JdbcTemplate jdbc;

    public JobDao(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    protected JdbcTemplate jdbc() { return jdbc; }

    private static final RowMapper<JobDefinition> MAPPER = (rs, i) -> {
        JobDefinition d = new JobDefinition();
        d.setId(rs.getLong("id"));
        d.setName(rs.getString("name"));
        d.setJobClass(rs.getString("job_class"));
        d.setCronExpr(rs.getString("cron_expr"));
        d.setZone(rs.getString("zone"));
        d.setMisfire(MisfireInstruction.valueOf(rs.getString("misfire")));
        d.setConcurrentExecutionDisallowed(rs.getBoolean("concurrent_execution_disallowed"));
        d.setState(JobState.valueOf(rs.getString("state")));
        Timestamp nft = rs.getTimestamp("next_fire_time");
        d.setNextFireTime(nft == null ? null : nft.toInstant());
        Timestamp ca = rs.getTimestamp("created_at");
        d.setCreatedAt(ca == null ? null : ca.toInstant());
        return d;
    };

    public long insert(JobDefinition job) {
        String sql = "INSERT INTO cron_jobs (name, job_class, cron_expr, zone, misfire, " +
                "concurrent_execution_disallowed, state, next_fire_time, created_at) " +
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)";
        KeyHolder kh = new GeneratedKeyHolder();
        jdbc.update(c -> {
            PreparedStatement ps = c.prepareStatement(sql, new String[]{"id"});
            ps.setString(1, job.getName());
            ps.setString(2, job.getJobClass());
            ps.setString(3, job.getCronExpr());
            ps.setString(4, job.getZone());
            ps.setString(5, job.getMisfire().name());
            ps.setBoolean(6, job.isConcurrentExecutionDisallowed());
            ps.setString(7, job.getState().name());
            ps.setTimestamp(8, job.getNextFireTime() == null ? null : Timestamp.from(job.getNextFireTime()));
            ps.setTimestamp(9, Timestamp.from(job.getCreatedAt() == null ? Instant.now() : job.getCreatedAt()));
            return ps;
        }, kh);
        return kh.getKey().longValue();
    }

    public Optional<JobDefinition> findById(long id) {
        List<JobDefinition> rs = jdbc.query("SELECT * FROM cron_jobs WHERE id = ?", MAPPER, id);
        return rs.isEmpty() ? Optional.empty() : Optional.of(rs.get(0));
    }

    public Optional<JobDefinition> findByName(String name) {
        List<JobDefinition> rs = jdbc.query("SELECT * FROM cron_jobs WHERE name = ?", MAPPER, name);
        return rs.isEmpty() ? Optional.empty() : Optional.of(rs.get(0));
    }

    public List<JobDefinition> findActiveDue(Instant now) {
        return jdbc.query(
                "SELECT * FROM cron_jobs WHERE state = 'ACTIVE' AND next_fire_time IS NOT NULL AND next_fire_time <= ?",
                MAPPER,
                Timestamp.from(now));
    }

    public void updateNextFireTime(long jobId, Instant nextFireTime) {
        jdbc.update("UPDATE cron_jobs SET next_fire_time = ? WHERE id = ?",
                nextFireTime == null ? null : Timestamp.from(nextFireTime), jobId);
    }

    public void updateState(long jobId, JobState state) {
        jdbc.update("UPDATE cron_jobs SET state = ? WHERE id = ?", state.name(), jobId);
    }

    public List<JobDefinition> findAll() {
        return jdbc.query("SELECT * FROM cron_jobs ORDER BY id", MAPPER);
    }
}
JAVA

# ---------- ExecutionDao.java ----------
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
import java.sql.Statement;
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
        // Atomic single-row claim with status-versioned UPDATE.
        List<Long> ids = jdbc.queryForList(
                "SELECT id FROM cron_executions WHERE status = 'PENDING' ORDER BY scheduled_time ASC, id ASC LIMIT 8",
                Long.class);
        for (Long id : ids) {
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

    public List<JobExecution> findStaleClaimed(Instant heartbeatBefore) {
        return jdbc.query(
                "SELECT * FROM cron_executions WHERE status IN ('CLAIMED','RUNNING') AND last_heartbeat IS NOT NULL " +
                        "AND last_heartbeat < ?",
                MAPPER, Timestamp.from(heartbeatBefore));
    }
}
JAVA

# ---------- SchedulerLoop.java ----------
cat > /app/src/main/java/com/snorkel/chronos/scheduler/SchedulerLoop.java <<'JAVA'
package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.cron.QuartzCronExpression;
import com.snorkel.chronos.domain.JobDefinition;
import com.snorkel.chronos.repository.ExecutionDao;
import com.snorkel.chronos.repository.JobDao;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;

@Component
public class SchedulerLoop {

    private static final Logger LOG = LoggerFactory.getLogger(SchedulerLoop.class);

    protected final JobDao jobDao;
    protected final JobDispatcher dispatcher;
    protected final MisfireHandler misfireHandler;
    protected final ExecutionDao execDao;
    protected final SchedulerConfig cfg;
    protected final Clock clock;
    protected volatile boolean running = false;
    protected Thread thread;

    public SchedulerLoop(JobDao jobDao,
                         JobDispatcher dispatcher,
                         MisfireHandler misfireHandler,
                         ExecutionDao execDao,
                         SchedulerConfig cfg,
                         Clock clock) {
        this.jobDao = jobDao;
        this.dispatcher = dispatcher;
        this.misfireHandler = misfireHandler;
        this.execDao = execDao;
        this.cfg = cfg;
        this.clock = clock;
    }

    @PostConstruct
    public void start() {
        running = true;
        thread = new Thread(this::loop, "chronos-scheduler-loop");
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
            try {
                tick();
            } catch (Throwable t) {
                LOG.warn("scheduler tick error", t);
            }
            try {
                Thread.sleep(cfg.getScheduler().getPollIntervalMs());
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }

    protected void tick() {
        Instant now = clock.instant();
        List<JobDefinition> due = jobDao.findActiveDue(now);
        boolean signal = false;
        for (JobDefinition def : due) {
            if (misfireHandler.isMisfired(def, now)) {
                misfireHandler.applyPolicy(def, now);
            } else {
                execDao.insertPending(def.getId(), def.getNextFireTime(), 0);
                Instant nxt = misfireHandler.computeNextAfter(def, def.getNextFireTime());
                jobDao.updateNextFireTime(def.getId(), nxt);
            }
            signal = true;
        }
        if (signal) dispatcher.signalNewWork();
    }
}
JAVA

# ---------- MisfireHandler.java ----------
cat > /app/src/main/java/com/snorkel/chronos/scheduler/MisfireHandler.java <<'JAVA'
package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.cron.QuartzCronExpression;
import com.snorkel.chronos.domain.ExecutionStatus;
import com.snorkel.chronos.domain.JobDefinition;
import com.snorkel.chronos.repository.ExecutionDao;
import com.snorkel.chronos.repository.JobDao;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;

@Component
public class MisfireHandler {

    protected final JobDao jobDao;
    protected final ExecutionDao execDao;
    protected final SchedulerConfig cfg;
    protected final Clock clock;

    public MisfireHandler(JobDao jobDao, ExecutionDao execDao, SchedulerConfig cfg, Clock clock) {
        this.jobDao = jobDao;
        this.execDao = execDao;
        this.cfg = cfg;
        this.clock = clock;
    }

    public void handleResume(JobDefinition def, Instant now) {
        if (isMisfired(def, now)) {
            applyPolicy(def, now);
        }
    }

    public boolean isMisfired(JobDefinition def, Instant now) {
        if (def.getNextFireTime() == null) return false;
        long delta = now.getEpochSecond() - def.getNextFireTime().getEpochSecond();
        return delta > cfg.getMisfire().getThresholdSeconds();
    }

    public void applyPolicy(JobDefinition def, Instant now) {
        switch (def.getMisfire()) {
            case FIRE_NOW -> {
                execDao.insertPending(def.getId(), now, 0);
                Instant nxt = computeNextAfter(def, now);
                jobDao.updateNextFireTime(def.getId(), nxt);
            }
            case DO_NOTHING -> {
                Instant nxt = computeNextAfter(def, now);
                jobDao.updateNextFireTime(def.getId(), nxt);
            }
            case FIRE_NEXT_WITH_REMAINING_COUNT -> {
                execDao.insertMisfiredSummary(def.getId(), def.getNextFireTime());
                Instant nxt = computeNextAfter(def, now);
                jobDao.updateNextFireTime(def.getId(), nxt);
            }
        }
    }

    public Instant computeNextAfter(JobDefinition def, Instant after) {
        ZoneId zone = ZoneId.of(def.getZone());
        QuartzCronExpression expr = QuartzCronExpression.parse(def.getCronExpr());
        ZonedDateTime nxt = expr.nextExecutionTime(after.atZone(zone));
        return nxt == null ? null : nxt.toInstant();
    }
}
JAVA

# ---------- JobDispatcher.java (single-threaded for M2) ----------
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
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.Semaphore;

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
        // Single worker for milestone 2; expanded in milestone 3.
        Thread t = new Thread(() -> workerLoop("worker-0"), "chronos-worker-0");
        t.setDaemon(true);
        t.start();
        workers.add(t);
    }

    @PreDestroy
    public void stop() {
        running = false;
        signal.release(workers.size());
        for (Thread t : workers) t.interrupt();
    }

    public void signalNewWork() {
        signal.release();
    }

    protected void workerLoop(String workerId) {
        while (running) {
            try {
                Optional<Long> claimed = execDao.claimNextPending(workerId, clock.instant());
                if (claimed.isEmpty()) {
                    signal.tryAcquire(500, java.util.concurrent.TimeUnit.MILLISECONDS);
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
        execDao.markStarted(execId, workerId, clock.instant());
        runningJobs.register(execId, Thread.currentThread());
        heartbeats.track(execId);
        try {
            JobBean bean = registry.lookup(job.getJobClass());
            String result = bean.execute(new JobContext(execId, job.getId(), e.getScheduledTime(), e.getRecoveryAttempt()));
            execDao.markCompleted(execId, ExecutionStatus.SUCCEEDED, clock.instant(), result);
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

# ---------- HeartbeatRegistrar.java (minimal — track/untrack only, no DB writes till M3) ----------
cat > /app/src/main/java/com/snorkel/chronos/scheduler/HeartbeatRegistrar.java <<'JAVA'
package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.repository.ExecutionDao;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class HeartbeatRegistrar {

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
            try {
                tick();
            } catch (Throwable t) { /* swallow */ }
            try { Thread.sleep(cfg.getHeartbeat().getIntervalMs()); }
            catch (InterruptedException ie) { Thread.currentThread().interrupt(); return; }
        }
    }

    protected void tick() {
        // M2: nothing yet — M3 fills in heartbeat DB writes.
    }
}
JAVA

# ---------- FailoverDetector.java (no-op for M2) ----------
cat > /app/src/main/java/com/snorkel/chronos/scheduler/FailoverDetector.java <<'JAVA'
package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.repository.ExecutionDao;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.springframework.stereotype.Component;

import java.time.Clock;

@Component
public class FailoverDetector {

    protected final ExecutionDao execDao;
    protected final SchedulerConfig cfg;
    protected final Clock clock;
    protected volatile boolean running = false;
    protected Thread thread;

    public FailoverDetector(ExecutionDao execDao, SchedulerConfig cfg, Clock clock) {
        this.execDao = execDao;
        this.cfg = cfg;
        this.clock = clock;
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
            try { tick(); } catch (Throwable t) { /* swallow */ }
            try { Thread.sleep(5_000L); } catch (InterruptedException ie) { Thread.currentThread().interrupt(); return; }
        }
    }

    protected void tick() { /* M3 fills in. */ }
}
JAVA

mvn -B -q -DskipTests -o package
cp /app/target/chronos.jar /app/chronos.jar
echo "M2 oracle complete"
