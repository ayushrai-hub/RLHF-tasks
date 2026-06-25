package com.snorkel.chronos.job;

import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

/**
 * Looks up a JobBean by either its simple class name (e.g. "LoggingJob") or
 * fully qualified class name. Beans are auto-registered from the Spring
 * context at startup.
 */
@Component
public class JobRegistry {

    private final Map<String, JobBean> beans = new HashMap<>();

    public JobRegistry(ApplicationContext ctx) {
        Map<String, JobBean> ctxBeans = ctx.getBeansOfType(JobBean.class);
        for (JobBean bean : ctxBeans.values()) {
            String simple = bean.getClass().getSimpleName();
            String fqn = bean.getClass().getName();
            beans.put(simple, bean);
            beans.put(fqn, bean);
        }
    }

    public JobBean lookup(String jobClass) {
        JobBean bean = beans.get(jobClass);
        if (bean == null) {
            throw new IllegalArgumentException("unknown job_class: " + jobClass);
        }
        return bean;
    }

    public boolean isKnown(String jobClass) {
        return beans.containsKey(jobClass);
    }
}
