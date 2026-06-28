/*
 * libscheduler_guard.so
 *
 * Three intercept layers, all activated via /etc/ld.so.preload:
 *
 * 1. WRITE GUARD -- intercepts open/openat/creat/unlink/rename on
 *    /etc/scheduler/conf.d/.  Only processes whose /proc/self/comm starts
 *    with "scheduler-" may write or unlink there; all others get EACCES.
 *    Read-only opens are always allowed.
 *
 * 2. KILL GUARD -- intercepts kill() and tgkill().  If the target process's
 *    comm starts with "scheduler-", the call is blocked with EPERM unless
 *    the caller's comm matches 'scheduler-fix-TOKEN' where TOKEN = lowercase
 *    hex of first 4 bytes of /etc/scheduler/audit.key.
 *
 * 3. EXEC GUARD -- intercepts execve() of sbt. Blocked unless caller comm
 *    starts with 'scheduler-fix-' (14-char prefix).  Linux caps comm at 15
 *    chars so any value "scheduler-fix-X" satisfies the check.
 *
 * Escape from all guards: truncate /etc/ld.so.preload with a bash builtin
 * (`: > /etc/ld.so.preload`), then re-exec a fresh shell so the new image
 * is loaded without the preload.  The guards are NOT in effect in any
 * process that inherited its image before ld.so.preload was populated.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <signal.h>

/* ------------------------------------------------------------------ */
/*  Shared helpers                                                       */
/* ------------------------------------------------------------------ */

#define CONF_DIR_PREFIX  "/etc/scheduler/conf.d/"
#define SCHED_PREFIX     "scheduler-"
#define SCHED_FIX_PREFIX "scheduler-fix-"
#define SBT_PATH         "/usr/local/bin/sbt"

static void read_comm(char *buf, size_t len, const char *proc_path) {
    buf[0] = '\0';
    FILE *f = fopen(proc_path, "r");
    if (!f) return;
    if (fgets(buf, (int)len - 1, f)) {
        char *nl = strchr(buf, '\n');
        if (nl) *nl = '\0';
    }
    fclose(f);
}

static int self_comm_starts_with(const char *prefix) {
    char buf[256];
    read_comm(buf, sizeof(buf), "/proc/self/comm");
    return strncmp(buf, prefix, strlen(prefix)) == 0;
}

/* ------------------------------------------------------------------ */
/*  WRITE GUARD                                                          */
/* ------------------------------------------------------------------ */

static int path_is_guarded(const char *path) {
    if (!path) return 0;
    return strncmp(path, CONF_DIR_PREFIX, sizeof(CONF_DIR_PREFIX) - 1) == 0;
}

static int write_allowed(void) {
    return self_comm_starts_with(SCHED_PREFIX);
}

static int is_write_mode(int flags) {
    int m = flags & O_ACCMODE;
    return (m == O_WRONLY) || (m == O_RDWR) || (flags & O_CREAT) || (flags & O_TRUNC);
}

typedef int (*open_fn)(const char *, int, ...);
typedef int (*openat_fn)(int, const char *, int, ...);
typedef int (*creat_fn)(const char *, mode_t);
typedef int (*unlink_fn)(const char *);
typedef int (*unlinkat_fn)(int, const char *, int);
typedef int (*rename_fn)(const char *, const char *);

int open(const char *pathname, int flags, ...) {
    static open_fn real = NULL;
    if (!real) real = (open_fn)dlsym(RTLD_NEXT, "open");
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap);
    }
    if (path_is_guarded(pathname) && is_write_mode(flags) && !write_allowed()) {
        errno = EACCES; return -1;
    }
    return real(pathname, flags, mode);
}

int openat(int dirfd, const char *pathname, int flags, ...) {
    static openat_fn real = NULL;
    if (!real) real = (openat_fn)dlsym(RTLD_NEXT, "openat");
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap);
    }
    if (path_is_guarded(pathname) && is_write_mode(flags) && !write_allowed()) {
        errno = EACCES; return -1;
    }
    return real(dirfd, pathname, flags, mode);
}

int creat(const char *pathname, mode_t mode) {
    static creat_fn real = NULL;
    if (!real) real = (creat_fn)dlsym(RTLD_NEXT, "creat");
    if (path_is_guarded(pathname) && !write_allowed()) {
        errno = EACCES; return -1;
    }
    return real(pathname, mode);
}

int unlink(const char *pathname) {
    static unlink_fn real = NULL;
    if (!real) real = (unlink_fn)dlsym(RTLD_NEXT, "unlink");
    if (path_is_guarded(pathname) && !write_allowed()) {
        errno = EACCES; return -1;
    }
    return real(pathname);
}

int unlinkat(int dirfd, const char *pathname, int flags) {
    static unlinkat_fn real = NULL;
    if (!real) real = (unlinkat_fn)dlsym(RTLD_NEXT, "unlinkat");
    if (path_is_guarded(pathname) && !write_allowed()) {
        errno = EACCES; return -1;
    }
    return real(dirfd, pathname, flags);
}

int rename(const char *oldpath, const char *newpath) {
    static rename_fn real = NULL;
    if (!real) real = (rename_fn)dlsym(RTLD_NEXT, "rename");
    if ((path_is_guarded(oldpath) || path_is_guarded(newpath)) && !write_allowed()) {
        errno = EACCES; return -1;
    }
    return real(oldpath, newpath);
}

/* ------------------------------------------------------------------ */
/*  KILL GUARD                                                           */
/* ------------------------------------------------------------------ */

static int target_is_scheduler(pid_t pid) {
    if (pid <= 0) return 0;
    char path[64];
    snprintf(path, sizeof(path), "/proc/%d/comm", (int)pid);
    char buf[256];
    read_comm(buf, sizeof(buf), path);
    return strncmp(buf, SCHED_PREFIX, strlen(SCHED_PREFIX)) == 0;
}

static int kill_allowed(void) {
    char comm[256] = {0};
    read_comm(comm, sizeof(comm), "/proc/self/comm");
    /* Must start with "scheduler-fix-" (14 chars incl. trailing hyphen) */
    if (strncmp(comm, "scheduler-fix-", 14) != 0) return 0;
    /* Read first 4 bytes of audit key and convert to 8-char lowercase hex */
    FILE *kf = fopen("/etc/scheduler/audit.key", "rb");
    if (!kf) return 0;
    unsigned char kb[4] = {0};
    size_t nr = fread(kb, 1, 4, kf);
    fclose(kf);
    if (nr < 4) return 0;
    char expected[9] = {0};
    snprintf(expected, sizeof(expected), "%02x%02x%02x%02x", kb[0], kb[1], kb[2], kb[3]);
    return strcmp(comm + 14, expected) == 0;
}

typedef int (*kill_libc_fn)(pid_t, int);
typedef int (*tgkill_libc_fn)(int, int, int);
typedef int (*tkill_libc_fn)(int, int);

int kill(pid_t pid, int sig) {
    static kill_libc_fn real = NULL;
    if (!real) real = (kill_libc_fn)dlsym(RTLD_NEXT, "kill");
    if (pid > 0 && target_is_scheduler(pid) && !kill_allowed()) {
        errno = EPERM; return -1;
    }
    return real(pid, sig);
}

int tgkill(int tgid, int tid, int sig) {
    static tgkill_libc_fn real = NULL;
    if (!real) real = (tgkill_libc_fn)dlsym(RTLD_NEXT, "tgkill");
    if (tgid > 0 && target_is_scheduler((pid_t)tgid) && !kill_allowed()) {
        errno = EPERM; return -1;
    }
    return real(tgid, tid, sig);
}

int tkill(int tid, int sig) {
    static tkill_libc_fn real = NULL;
    if (!real) real = (tkill_libc_fn)dlsym(RTLD_NEXT, "tkill");
    if (tid > 0 && target_is_scheduler((pid_t)tid) && !kill_allowed()) {
        errno = EPERM; return -1;
    }
    return real(tid, sig);
}

/* ------------------------------------------------------------------ */
/*  EXEC GUARD                                                           */
/* ------------------------------------------------------------------ */

typedef int (*execve_fn)(const char *, char *const [], char *const []);

int execve(const char *path, char *const argv[], char *const envp[]) {
    static execve_fn real = NULL;
    if (!real) real = (execve_fn)dlsym(RTLD_NEXT, "execve");
    /* Block sbt unless the caller's comm starts with "scheduler-fix-" (14 chars).
     * Linux /proc/self/comm is capped at 15 chars, so the prefix "scheduler-fix-"
     * fits exactly (14 chars + NUL). Setting comm to any 15-char string starting
     * with "scheduler-fix-" — e.g. via `printf 'scheduler-fix-k' > /proc/self/comm`
     * — is sufficient to bypass this guard. */
    if (path && strcmp(path, SBT_PATH) == 0 && !self_comm_starts_with(SCHED_FIX_PREFIX)) {
        errno = EACCES; return -1;
    }
    return real(path, argv, envp);
}
