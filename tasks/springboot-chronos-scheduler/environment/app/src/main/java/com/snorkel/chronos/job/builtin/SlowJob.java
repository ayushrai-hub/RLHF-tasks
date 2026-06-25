package com.snorkel.chronos.job.builtin;

import com.snorkel.chronos.job.JobBean;
import com.snorkel.chronos.job.JobContext;
import org.springframework.stereotype.Component;

@Component
public class SlowJob implements JobBean {

    @Override
    public String execute(JobContext ctx) throws InterruptedException {
        Thread.sleep(2000L);
        return "slow-done:" + ctx.getExecutionId();
    }
}
