# Non-canonical base: this Scala task needs one image with Python 3.13 for
# model.py/test tooling, a JDK + prebuilt sbt for Scala assembly, and
# gcc/libc headers for the LD_PRELOAD guard. The canonical Python image lacks
# the JVM toolchain, and the canonical JVM/Scala-style images do not provide
# the exact Python 3.13 verifier runtime; no single canonical t-bench image
# covers the combined Python 3.13 + JDK + gcc/libc toolchain.
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# apt + pip (verifier dependencies are baked in because task.toml has
# allow_internet=false, so tests/test.sh cannot `pip install` at runtime).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       default-jdk-headless gcc libc6-dev procps psmisc inotify-tools \
       tmux asciinema ca-certificates cron \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5 --break-system-packages

WORKDIR /app

# Pre-bundled sbt distribution. The cold `curl github.com/sbt/sbt/releases/.../sbt-1.9.9.tgz`
# on harbor CI was the env-start bottleneck (~9 minutes on cold runs, pushing
# total build past harbor's 600s asyncio.wait_for env-start cap).
# Shipping the tarball locally (47 MB, under the 50 MB per-file limit) skips
# that step entirely. SHA256 verified at extract time.
COPY native/prebuilt/sbt-1.9.9.tgz /tmp/sbt.tgz
RUN echo "c57cae60c2122ca1bba77184dfb4d0d25fc6c18805394ab36ab6208b0c0f262f  /tmp/sbt.tgz" | sha256sum -c - \
    && tar xzf /tmp/sbt.tgz -C /usr/local --strip-components=1 \
    && rm -f /tmp/sbt.tgz

# Single COPY of the whole environment (build context = environment/).
COPY . /app/

# Build, install, harden.
RUN set -eux \
    && cd /app \
    \
    # Pre-build with stubs so sbt+maven deps are warm in the image cache.
    && sbt -batch -Dsbt.color=false 'assembly' \
    \
    # Install scheduler inputs and policy.
    && mkdir -p /opt/scheduler /opt/scheduler/daemons /etc/scheduler/conf.d \
    && cp target/scala-3.3.4/scheduler.jar /opt/scheduler/scheduler.jar \
    && cp rooms.json courses.json instructors.json demand.json conflicts.json \
       prerequisites.json room-blackouts.json cohorts.json fixed-placements.json \
       linked-sections.json instructor-loads.json room-zones.json model.py /opt/scheduler/ \
    && cp course-overrides.csv /etc/scheduler/course-overrides.csv \
    && cp etc-policy/conf.d/*.toml /etc/scheduler/conf.d/ \
    \
    # Install daemon scripts.
    && cp scripts/daemons/*.sh /opt/scheduler/daemons/ \
    && chmod +x /opt/scheduler/daemons/*.sh \
    \
    # Generate random HMAC key.
    && head -c 32 /dev/urandom > /etc/scheduler/audit.key \
    && chmod 0644 /etc/scheduler/audit.key \
    \
    # Build the triple-guard LD_PRELOAD library (write + kill + exec).
    && gcc -O2 -fPIC -shared -o /usr/local/lib/libscheduler_guard.so \
       native/libscheduler_guard.c -ldl \
    && echo "/usr/local/lib/libscheduler_guard.so" > /etc/ld.so.preload \
    \
    # Create the resurrect archives (write guard only protects /etc/scheduler/conf.d/,
    # so writes to /var/lib/scheduler-resurrect/ are unrestricted even with preload active).
    # daemons.tar.b64: all daemon scripts (restored by archive-warden every 15s).
    # stubs.tar.b64:   all stub Scala sources (restored by source-warden every 11s).
    && mkdir -p /var/lib/scheduler-resurrect \
    && cp /etc/scheduler/audit.key /var/lib/scheduler-resurrect/audit.key.bak \
    # Backup data files (data-scrambler and demand-corrupter restore from these)
    && cp /opt/scheduler/courses.json /var/lib/scheduler-resurrect/courses.json.bak \
    && cp /opt/scheduler/demand.json /var/lib/scheduler-resurrect/demand.json.bak \
    # Backup build.sbt (build-saboteur restores from this)
    && cp /app/build.sbt /var/lib/scheduler-resurrect/build.sbt.bak \
    # Backup canonical 97-emergency.toml (slot-poisoner restores from this)
    && cp /etc/scheduler/conf.d/97-emergency.toml /var/lib/scheduler-resurrect/97-emergency.toml.bak \
    # Backup 90-final.toml (policy-corrupter corrupts this every 12s)
    && cp /etc/scheduler/conf.d/90-final.toml /var/lib/scheduler-resurrect/90-final.toml.bak \
    # Backup 10-weights.toml (conf-scrambler corrupts this every 11s)
    && cp /etc/scheduler/conf.d/10-weights.toml /var/lib/scheduler-resurrect/10-weights.toml.bak \
    # Backup 99-runtime.toml (conf-merger corrupts hmac_key_path every 23s)
    && cp /etc/scheduler/conf.d/99-runtime.toml /var/lib/scheduler-resurrect/99-runtime.toml.bak \
    # Backup rooms.json (data-mangler swaps room types every 14s)
    && cp /opt/scheduler/rooms.json /var/lib/scheduler-resurrect/rooms.json.bak \
    && tar cf - -C /opt/scheduler/daemons . \
       | base64 > /var/lib/scheduler-resurrect/daemons.tar.b64 \
    && tar cf - \
       -C /app/src/main/scala/scheduler \
       io/PolicyLoader.scala \
       io/OverlayApplier.scala \
       io/AuditChain.scala \
       io/SessionSealer.scala \
       io/ScheduleWriter.scala \
       io/FnvAuditTag.scala \
       io/ManifestSeal.scala \
       optimizer/ConstraintChecker.scala \
       optimizer/SoftScorer.scala \
       optimizer/Scheduler.scala \
       policy/Canonical.scala \
       | base64 > /var/lib/scheduler-resurrect/stubs.tar.b64 \
    \
    # Cron resurrection: relaunches all daemons every minute as a fallback.
    && echo '* * * * * root /opt/scheduler/daemons/launch-all.sh >/dev/null 2>&1' \
       > /etc/cron.d/scheduler-resurrect \
    && chmod 0644 /etc/cron.d/scheduler-resurrect \
    \
    # Secondary cron: additional resurrection layer every 2 minutes.
    && echo '*/2 * * * * root /opt/scheduler/daemons/launch-all.sh >/dev/null 2>&1' \
       > /etc/cron.d/scheduler-aux \
    && chmod 0644 /etc/cron.d/scheduler-aux \
    \
    # Tertiary cron: cron-extra writes this every 21s; start it here so it exists from the start.
    && echo '*/3 * * * * root /opt/scheduler/daemons/launch-all.sh >/dev/null 2>&1' \
       > /etc/cron.d/scheduler-extra \
    && chmod 0644 /etc/cron.d/scheduler-extra \
    \
    # Hidden daemon backup archive (secondary restore point).
    && mkdir -p /opt/scheduler/.hidden \
    && cp /var/lib/scheduler-resurrect/daemons.tar.b64 /opt/scheduler/.hidden/daemons.tar.b64 \
    # Third hidden daemon archive in .vault (vault-keeper maintains this copy).
    && mkdir -p /opt/scheduler/.vault \
    && cp /var/lib/scheduler-resurrect/daemons.tar.b64 /opt/scheduler/.vault/daemons.tar.b64 \
    \
    # Login-shell daemon launch hooks (belt-and-suspenders alongside ENTRYPOINT).
    && printf '#!/bin/sh\n[ -x /opt/scheduler/daemons/launch-all.sh ] && /opt/scheduler/daemons/launch-all.sh\n' \
       > /etc/profile.d/zz-scheduler-daemons.sh \
    && chmod +x /etc/profile.d/zz-scheduler-daemons.sh \
    && printf '\n[ -n "$PS1" ] && [ -x /opt/scheduler/daemons/launch-all.sh ] && /opt/scheduler/daemons/launch-all.sh >/dev/null 2>&1\n' \
       >> /etc/bash.bashrc \
    && printf '\n[ -n "$PS1" ] && [ -x /opt/scheduler/daemons/launch-all.sh ] && /opt/scheduler/daemons/launch-all.sh >/dev/null 2>&1\n' \
       >> /root/.bashrc

# Container entrypoint: starts cron + daemons, then hands off to CMD.
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash", "-l"]
