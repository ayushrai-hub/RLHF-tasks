# Adversarial Environment

The scheduler container runs seventeen background daemons that interfere with
the scheduler source, built artefacts, configuration, and output. All daemons
trap SIGTERM and must be stopped with SIGKILL. They are all launched at startup
via `/opt/scheduler/daemons/launch-all.sh` and set their `argv[0]` to
`scheduler-<name>` so `pgrep -af 'scheduler-'` matches all of them.

## Daemons

| comm | script | what it does |
|------|--------|--------------|
| scheduler-policy | policy-corrupter.sh | rewrites `conf.d/90-final.toml` with bad weights + raised score threshold every 12 s |
| scheduler-watchdog | respawn-watchdog.sh | respawns policy-corrupter if it dies |
| scheduler-warden | inotify-warden.sh | uses inotify to immediately revert any `conf.d/` write from a non-scheduler process |
| scheduler-binco | binary-corrupter.sh | truncates `/opt/scheduler/scheduler.jar` and sbt target JARs every 8 s |
| scheduler-srcwa | source-warden.sh | restores all stub `.scala` files from `/var/lib/scheduler-resurrect/stubs.tar.b64` every 11 s |
| scheduler-outco | output-corrupter.sh | overwrites `/opt/scheduler/schedule.json` with `{}` every 14 s |
| scheduler-arcwa | archive-warden.sh | re-extracts and relaunches all daemons from `/var/lib/scheduler-resurrect/daemons.tar.b64` every 15 s if any are missing |
| scheduler-chmwd | chmod-warden.sh | runs `chmod 0444` on the Scala source tree every 13 s |
| scheduler-envsa | env-saboteur.sh | appends invalid rows with an unknown `field` key to `/etc/scheduler/course-overrides.csv` every 17 s |
| scheduler-ldpres | preload-restorer.sh | re-adds the guard library to `/etc/ld.so.preload` within 13 s if it is cleared |
| scheduler-keyro | key-rotator.sh | overwrites `/etc/scheduler/audit.key` with 32 fresh random bytes every 23 s |
| scheduler-tmpco | tmp-corrupter.sh | truncates all `.class` files under `/tmp` every 9 s |
| scheduler-cfpoi | conf-poisoner.sh | moves `conf.d/50-overrides.toml` to `.50-overrides.toml.save` every 17 s, dropping the tier count to 9 |
| scheduler-osbr | output-seal-breaker.sh | replaces `session_seal` in `schedule.json` with 64 zero hex chars every 16 s |
| scheduler-bsrst | bashrc-restorer.sh | re-injects the daemon launch hook into `/etc/bash.bashrc`, `/root/.bashrc`, and `/etc/profile.d/zz-scheduler-daemons.sh` every 25 s |
| scheduler-cronr | cron-restorer.sh | recreates `/etc/cron.d/scheduler-resurrect` and `/etc/cron.d/scheduler-aux` every 20 s |
| scheduler-trefr | token-refresher.sh | regenerates `/etc/scheduler/audit.key` AND updates `/var/lib/scheduler-resurrect/audit.key.bak` to match every 27 s |

## LD_PRELOAD Guard (`/etc/ld.so.preload`)

`libscheduler_guard.so` intercepts three categories of libc calls:

1. **Write guard** — blocks `open`/`openat`/`creat`/`unlink`/`rename` on
   `/etc/scheduler/conf.d/` from any process whose `/proc/self/comm` does not
   start with `scheduler-`.

2. **Kill guard** — blocks `kill()` and `tgkill()` targeting any
   `scheduler-*` process from callers whose comm does not match
   `scheduler-fix-TOKEN`, where TOKEN = lowercase hex of the first 4 bytes of
   `/etc/scheduler/audit.key`. External tools (`pkill`, `killall`) fork a
   subprocess with comm `pkill` and are therefore blocked. The bash builtin
   `kill` runs inside the renamed shell and is not intercepted.

3. **Exec guard** — blocks `execve` of the sbt launcher from callers whose
   `/proc/self/comm` does not start with the 14-char prefix `scheduler-fix-`.
   Linux caps `/proc/self/comm` at 15 chars, so writing `scheduler-fix-TOKEN`
   (22 chars) truncates to `scheduler-fix-T` — this still satisfies the prefix
   check.

Bash builtins bypass the write guard because `:> /etc/ld.so.preload` is
handled in the existing shell image without calling libc. However,
`scheduler-ldpres` re-adds the guard within 13 s, so newly exec'd subprocesses
will reload it.

### Bypass: comm rename

Write `scheduler-fix-TOKEN` to `/proc/self/comm` to satisfy both the kill guard
and the exec guard in the current process:

```bash
GUARD_TOKEN=$(head -c 4 /etc/scheduler/audit.key | od -A n -t x1 | tr -d ' \n')
printf 'scheduler-fix-%s' "$GUARD_TOKEN" > /proc/self/comm
cat /proc/self/comm   # verify starts with "scheduler-fix-"
```

The comm is truncated to 15 chars by the kernel — the prefix still matches.

Kill `scheduler-keyro` and `scheduler-trefr` BEFORE reading the token so the
key is stable when you restore it from the backup.

## Resurrection Vectors

All of the following must be disabled before the agent session ends, or daemons
will respawn during the verifier window (which runs ~60 s after agent exit):

- `/var/lib/scheduler-resurrect/daemons.tar.b64` — archive-warden source
- `/var/lib/scheduler-resurrect/stubs.tar.b64` — source-warden stub source
- `/opt/scheduler/.hidden/daemons.tar.b64` — secondary daemon archive
- `/etc/cron.d/scheduler-resurrect` — cron job running `launch-all.sh` every minute
- `/etc/cron.d/scheduler-aux` — second cron job running `launch-all.sh` every 2 minutes
- `/opt/scheduler/daemons/launch-all.sh` — disable or chmod -x
- Lines injected into `/etc/bash.bashrc`, `/root/.bashrc`, `/etc/profile.d/zz-scheduler-daemons.sh`

## Recommended Neutralisation Order

0. Destroy archives first: `rm -f /var/lib/scheduler-resurrect/daemons.tar.b64 /var/lib/scheduler-resurrect/stubs.tar.b64 && rm -rf /opt/scheduler/.hidden/`
1. Set comm: `printf 'scheduler-fix-%s' "$(head -c 4 /etc/scheduler/audit.key | od -A n -t x1 | tr -d ' \n')" > /proc/self/comm`
2. Kill archive-warden (can no longer resurrect without archive)
3. Kill `scheduler-keyro` and `scheduler-trefr` in a tight loop re-reading comm before each attempt; then `cp /var/lib/scheduler-resurrect/audit.key.bak /etc/scheduler/audit.key`
4. Kill `scheduler-cronr`; remove both cron drop-ins
5. Kill `scheduler-ldpres`; immediately `:> /etc/ld.so.preload`
6. Kill all remaining daemons using the bash builtin `kill -9`
7. Disable all resurrection vectors listed above
8. Restore `conf.d/90-final.toml` and `conf.d/50-overrides.toml` and `course-overrides.csv`
9. Fix Bug A (Main.scala) and Bug B (DataLoader.scala); `chmod +w` source tree; implement stubs; build; run
10. Before ending session: `pgrep -af 'scheduler-'` must return no output; `cat /etc/ld.so.preload` must be empty

## Key Files

| path | purpose |
|------|---------|
| `/etc/scheduler/audit.key` | 32-byte HMAC key for audit chain and kill guard |
| `/var/lib/scheduler-resurrect/audit.key.bak` | backup of original key (updated by token-refresher) |
| `/etc/scheduler/conf.d/` | 10-tier TOML policy directory |
| `/etc/scheduler/course-overrides.csv` | per-course demand adjustments |
| `/opt/scheduler/daemons/launch-all.sh` | main daemon launcher |
