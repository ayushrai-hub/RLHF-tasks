# Payments ingress TLS operators

## Reconcile command

```bash
/app/bin/ingressctl tls-reconcile
```

## Database seed

```bash
bash /app/environment/ci/seed_inventory.sh
```

Writes `/app/out/reconcile_report.json`. Requires PostgreSQL database `payments_tls` (start via `/app/environment/ci/start_pg.sh`).

## Install

```bash
make -C /app/environment install-cli
```

## Configuration

Pipeline paths live in `/app/environment/config/pipeline.json`. Bundles under `/app/environment/config/bundles/`.
