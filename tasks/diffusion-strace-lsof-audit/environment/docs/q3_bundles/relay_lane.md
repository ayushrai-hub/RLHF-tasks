# Relay lane

Cross-host relay checkpoint left hex-encoded ports and stale inode paths in the trace.

<!-- shell-invoke -->
./bin/diffusion-sample --seed 8800 --steps 80 --run-dir /var/lib/diffusion-runs/current

```strace
88150 connect(6, {sa_family=AF_INET, sin_addr=inet_addr("198.51.100.42"), sin_port=htons(0x1BB)}, 16) = 0
88150 openat(AT_FDCWD, "/var/lib/diffusion-runs/current/relay.log", O_APPEND) = 7
88150 connect(8, {sa_family=AF_INET6, sin6_port=htons(443), sin6_addr=inet_pton(AF_INET6, "::1")}, 28) = 0
88150 connect(9, {sa_family=AF_INET6, sin6_port=htons(0x01BB), sin6_addr=inet_pton(AF_INET6, "2001:db8::5")}, 28) = 0
```

```lsof
88150 python  6u  IPv4  0t0  TCP 10.0.0.8:60444->198.51.100.42:https (ESTABLISHED)
88150 python  7w  REG  253,0  64  /var/lib/diffusion-runs/current/relay.log (deleted)
88150 python  9u  IPv6  0t0  TCP [2001:db8::5]:443 (ESTABLISHED)
88150 python  10w  REG  253,0  0  /etc/diffusion/stale/relay.bin (deleted)
```
