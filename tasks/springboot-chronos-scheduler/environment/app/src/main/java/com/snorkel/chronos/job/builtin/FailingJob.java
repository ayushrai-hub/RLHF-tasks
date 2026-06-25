package com.snorkel.chronos.job.builtin;

import com.snorkel.chronos.job.JobBean;
import com.snorkel.chronos.job.JobContext;
import org.springframework.stereotype.Component;

@Component
public class FailingJob implements JobBean {

    @Override
    public String execute(JobContext ctx) {
        throw new RuntimeException("intentional failure for execution " + ctx.getExecutionId());
    }
}
