package com.snorkel.chronos.repository;

import com.snorkel.chronos.domain.JobDefinition;
import com.snorkel.chronos.domain.JobState;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

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

    public long insert(JobDefinition job) {
        throw new UnsupportedOperationException("milestone 2: implement JobDao.insert");
    }

    public Optional<JobDefinition> findById(long id) {
        throw new UnsupportedOperationException("milestone 2: implement JobDao.findById");
    }

    public Optional<JobDefinition> findByName(String name) {
        throw new UnsupportedOperationException("milestone 2: implement JobDao.findByName");
    }

    public List<JobDefinition> findActiveDue(Instant now) {
        throw new UnsupportedOperationException("milestone 2: implement JobDao.findActiveDue");
    }

    public void updateNextFireTime(long jobId, Instant nextFireTime) {
        throw new UnsupportedOperationException("milestone 2: implement JobDao.updateNextFireTime");
    }

    public void updateState(long jobId, JobState state) {
        throw new UnsupportedOperationException("milestone 2: implement JobDao.updateState");
    }

    public List<JobDefinition> findAll() {
        throw new UnsupportedOperationException("milestone 2: implement JobDao.findAll");
    }
}
