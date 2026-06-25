# Replay lane

Replay without persisting the seed flag in the operator notes.

<!-- shell-invoke -->
./bin/diffusion-sample --steps 1200 --run-dir /var/lib/diffusion-runs/current

```strace
44102 openat(AT_FDCWD, "/var/lib/diffusion-runs/current/checkpoint.dat", O_RDWR|O_CREAT, 0644) = 7
44102 write(7, "frame", 5) = 5
44102 close(7) = 0
```

```lsof
44102 python  7u  REG  253,0  16384  /var/lib/diffusion-runs/current/checkpoint.dat
```
