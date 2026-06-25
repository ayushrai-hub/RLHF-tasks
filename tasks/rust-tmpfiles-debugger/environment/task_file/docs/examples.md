# Examples

Given these entries:

```text
/var/cache/app/old.log file 0644 root root 240
/var/cache/app/new.log file 0644 root root 2
```

and this config:

```text
x /var/cache/app/new.log - - - - -
r /var/cache/app/*.log - - - 7d -
d /run/app 0750 app app - -
```

the plan removes `/var/cache/app/old.log` and creates `/run/app`. The newer log
is excluded from cleanup and is too young for `7d` anyway.

If `/etc/tmpfiles.d/cache.conf` and `/usr/lib/tmpfiles.d/cache.conf` are both
provided, only the `/etc` file is used for that basename. Recursive cleanup with
`R /var/tmp/app - - - 1w -` removes old paths under `/var/tmp/app`, but an
exclude such as `x /var/tmp/app/keep - - - - -` protects that path and prevents
a parent-directory remove action that would delete it indirectly.

A create or adjust rule does not protect a path from cleanup. If
`z /var/tmp/app/old 0600 app app - -` claims an existing old file and
`R /var/tmp/app - - - 1w -` also reaches that file, the plan may include both an
adjust and a remove for `/var/tmp/app/old`. However, if `R` removes the parent
directory itself, child remove actions under that parent are omitted.
