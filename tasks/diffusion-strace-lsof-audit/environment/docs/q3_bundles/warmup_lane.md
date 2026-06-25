# Warmup lane

Operator warmup with seeded sampler.

<!-- shell-invoke -->
./bin/diffusion-sample --seed 4242 --steps 200 --run-dir /var/lib/diffusion-runs/current

```strace
99120 openat(AT_FDCWD, "/var/lib/diffusion-runs/current/manifest.json", O_RDONLY) = 3
99120 openat(AT_FDCWD, "/var/lib/diffusion-runs/current/lattice.bin", O_RDONLY) = 4
99120 write(3, "ok", 2) = 2
99120 connect(3, {sa_family=AF_INET, sin_port=htons(8443), sin_addr=inet_addr("127.0.0.1")}, 16) = 0
99120 close(3) = 0
99120 close(4) = 0
```

```lsof
99120 python  3u  REG  253,0  4096  /var/lib/diffusion-runs/current/manifest.json
99120 python  4u  REG  253,0  8192  /var/lib/diffusion-runs/current/lattice.bin
```

```lsof
99120 python  3u  REG  253,0  4096  /var/lib/diffusion-runs/current/manifest.json
99120 python  4u  REG  253,0  8192  /var/lib/diffusion-runs/current/lattice.bin
      python  5u  REG  253,0  1024  /var/lib/diffusion-runs/current/warmup.cache
      python  6u  REG  253,0  1024  /var/lib/diffusion-runs/current/warmup.cache
      python  7u  REG  253,0  1024  /var/lib/diffusion-runs/current/warmup.cache
      python  8u  REG  253,0  1024  /var/lib/diffusion-runs/current/warmup.cache
```
