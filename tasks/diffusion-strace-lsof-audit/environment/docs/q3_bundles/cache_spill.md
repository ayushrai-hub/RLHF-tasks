# Cache spill lane

State file escaped the run directory during a resume attempt.

<!-- shell-invoke -->
./bin/diffusion-sample --seed 77 --steps 400 --run-dir /var/lib/diffusion-runs/current

```strace
55110 openat(AT_FDCWD, "/etc/diffusion/cache/state.bin", O_WRONLY|O_CREAT, 0644) = 8
55110 write(8, "spill", 5) = 5
55110 openat(AT_FDCWD, "/var/tmp/diffusion/spill.bin", O_WRONLY|O_CREAT, 0644) = 10
55110 openat(AT_FDCWD, "/var/lib/diffusion-runs/current/trace.log", O_APPEND) = 9
55110 write(9, "note", 4) = 4
```

```lsof
55110 python  8w  REG  253,0  2048  /etc/diffusion/cache/state.bin
55110 python  9w  REG  253,0  1024  /var/lib/diffusion-runs/current/trace.log
```
