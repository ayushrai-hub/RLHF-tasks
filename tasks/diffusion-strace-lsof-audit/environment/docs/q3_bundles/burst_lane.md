# Burst lane

Malformed replay burst left handles open.

<!-- shell-invoke -->
./bin/diffusion-sample --steps 64 --run-dir /var/lib/diffusion-runs/current

```strace
66120 openat(AT_FDCWD, "/var/lib/diffusion-runs/current/work/a.bin", O_RDONLY) = 10
66120 openat(AT_FDCWD, "/var/lib/diffusion-runs/current/work/b.bin", O_RDONLY) = 11
66120 openat(AT_FDCWD, "/tmp/diffusion-run/scratch.dat", O_RDWR|O_CREAT, 0644) = 12
66120 write(12, "tmp", 3) = 3
```

```lsof
66120 python  10r  REG  253,0  512  /var/lib/diffusion-runs/current/work/a.bin
      python  11r  REG  253,0  512  /var/lib/diffusion-runs/current/work/b.bin
      python  12u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
      python  13u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
      python  14u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
      python  15u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
```

```lsof
66120 python  10r  REG  253,0  512  /var/lib/diffusion-runs/current/work/a.bin
      python  11r  REG  253,0  512  /var/lib/diffusion-runs/current/work/b.bin
      python  12u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
      python  13u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
      python  14u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
      python  15u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
      python  16u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
      python  17u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
      python  18u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
      python  19u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
      python  20u  REG  253,0  256  /tmp/diffusion-run/scratch.dat
```
