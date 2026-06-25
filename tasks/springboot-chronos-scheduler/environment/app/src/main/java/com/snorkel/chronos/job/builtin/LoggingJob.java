package com.snorkel.chronos.job.builtin;

import com.snorkel.chronos.job.JobBean;
import com.snorkel.chronos.job.JobContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.Instant;

@Component
public class LoggingJob implements JobBean {

    private static final Logger LOG = LoggerFactory.getLogger(LoggingJob.class);

    @Override
    public String execute(JobContext ctx) {
        String marker = "logged-at:" + Instant.now().toString();
        LOG.info("LoggingJob exec={} job={} scheduled={} -> {}",
                ctx.getExecutionId(), ctx.getJobId(), ctx.getScheduledTime(), marker);
        return marker;
    }
}
