package com.snorkel.chronos.scheduler;

import com.snorkel.chronos.config.SchedulerConfig;
import com.snorkel.chronos.repository.ExecutionDao;
import com.snorkel.chronos.repository.JobDao;
import com.snorkel.chronos.job.JobRegistry;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Semaphore;

/**
 * Owns the worker thread pool. Workers poll the executions table for PENDING
 * rows, atomically claim one (CLAIMED → RUNNING), execute the job, register
 * the running thread for heartbeat tracking, then mark completion.
 *
 * signalNewWork() releases the work semaphore so workers don't have to wait
 * for the poll interval after an immediate trigger.
 *
 * Agent owns the worker body in milestone 2 (basic dispatch) and milestone 3
 * (claim via SELECT FOR UPDATE + concurrent_execution_disallowed + heartbeat).
 */
@Component
public class JobDispatcher {

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

    public JobDispatcher(JobDao jobDao,
                         ExecutionDao execDao,
                         JobRegistry registry,
                         RunningJobsRegistry runningJobs,
                         HeartbeatRegistrar heartbeats,
                         SchedulerConfig cfg,
                         Clock clock) {
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

    public void signalNewWork() {
        signal.release();
    }

    protected void workerLoop(String workerId) {
        throw new UnsupportedOperationException("milestone 2: implement JobDispatcher.workerLoop");
    }
}
