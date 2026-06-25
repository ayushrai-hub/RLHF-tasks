package com.snorkel.chronos.repository;

import com.snorkel.chronos.domain.ExecutionStatus;
import com.snorkel.chronos.domain.JobExecution;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

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

    public long insertPending(long jobId, Instant scheduledTime, int recoveryAttempt) {
        throw new UnsupportedOperationException("milestone 2: implement ExecutionDao.insertPending");
    }

    public long insertMisfiredSummary(long jobId, Instant scheduledTime) {
        throw new UnsupportedOperationException("milestone 2: implement ExecutionDao.insertMisfiredSummary");
    }

    public Optional<JobExecution> findById(long id) {
        throw new UnsupportedOperationException("milestone 2: implement ExecutionDao.findById");
    }

    public List<JobExecution> findByJob(long jobId, int limit) {
        throw new UnsupportedOperationException("milestone 2: implement ExecutionDao.findByJob");
    }

    public void markStatus(long execId, ExecutionStatus status, String errorMessage) {
        throw new UnsupportedOperationException("milestone 2: implement ExecutionDao.markStatus");
    }

    public void markStarted(long execId, String workerId, Instant startedAt) {
        throw new UnsupportedOperationException("milestone 3: implement ExecutionDao.markStarted");
    }

    public void markCompleted(long execId, ExecutionStatus status, Instant completedAt, String errorMessage) {
        throw new UnsupportedOperationException("milestone 3: implement ExecutionDao.markCompleted");
    }

    public void updateHeartbeat(long execId, Instant ts) {
        throw new UnsupportedOperationException("milestone 3: implement ExecutionDao.updateHeartbeat");
    }

    public Optional<Long> claimNextPending(String workerId, Instant now) {
        throw new UnsupportedOperationException("milestone 3: implement ExecutionDao.claimNextPending");
    }

    public int countActiveForJob(long jobId) {
        throw new UnsupportedOperationException("milestone 3: implement ExecutionDao.countActiveForJob");
    }

    public int countActiveExcluding(long jobId, long excludeExecId) {
        throw new UnsupportedOperationException("milestone 3: implement ExecutionDao.countActiveExcluding");
    }

    public List<JobExecution> findStaleClaimed(Instant heartbeatBefore) {
        throw new UnsupportedOperationException("milestone 3: implement ExecutionDao.findStaleClaimed");
    }
}
