# Toolchain

- Rust 1.81 via rustup (`/usr/local/cargo/bin`)
- GCC / make for HAL C sources
- Python 3 verifier venv at `/opt/verifier-venv`

Build the simulator:

```bash
cd /app/environment && cargo build --release --bin facility_sim
```

Regenerate trace output:

```bash
bash /app/environment/scripts/run_sim_driver.sh
```
