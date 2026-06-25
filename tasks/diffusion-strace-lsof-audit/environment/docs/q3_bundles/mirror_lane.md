# Mirror lane

Operator script pulled remote checksums during validation.

<!-- shell-invoke -->
./bin/diffusion-sample --seed 9001 --steps 50 --run-dir /var/lib/diffusion-runs/current && curl -fsS https://example.org/checksums

```strace
77120 connect(4, {sa_family=AF_INET, sin_port=htons(443), sin_addr=inet_addr("93.184.216.34")}, 16) = 0
77120 openat(AT_FDCWD, "/var/lib/diffusion-runs/current/mirror.log", O_APPEND) = 5
77120 write(5, "pull", 4) = 4
```

```lsof
77120 curl  4u  IPv4  0t0  TCP 10.0.0.4:52312->93.184.216.34:https (ESTABLISHED)
77120 curl  5w  REG  253,0  128  /var/lib/diffusion-runs/current/mirror.log
```
