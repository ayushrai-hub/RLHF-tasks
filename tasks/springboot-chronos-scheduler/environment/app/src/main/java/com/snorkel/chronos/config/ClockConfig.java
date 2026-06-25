package com.snorkel.chronos.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Wall-clock Clock plus a TestClock wrapper so the verifier can shift "now"
 * forward to drive misfire / failover scenarios deterministically. Production
 * code never reads {@link Clock#systemUTC()} directly; everything goes through
 * the injected {@link Clock}.
 */
@Configuration
public class ClockConfig {

    @Bean
    public TestClock chronosClock() {
        return new TestClock();
    }

    @Bean
    public Clock clock(TestClock testClock) {
        return testClock;
    }

    public static class TestClock extends Clock {

        private final AtomicReference<Duration> offset = new AtomicReference<>(Duration.ZERO);
        private final ZoneId zone = ZoneId.of("UTC");

        @Override
        public ZoneId getZone() { return zone; }

        @Override
        public Clock withZone(ZoneId zone) { return this; }

        @Override
        public Instant instant() {
            return Instant.now().plus(offset.get());
        }

        public void advance(Duration delta) {
            offset.updateAndGet(prev -> prev.plus(delta));
        }

        public Duration getOffset() {
            return offset.get();
        }

        public void reset() {
            offset.set(Duration.ZERO);
        }
    }
}
