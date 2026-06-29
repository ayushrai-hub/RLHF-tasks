# Kernel workspace notes

Simulation wrappers under `/app/workbook/kernels/` pin kernels through local `replace` directives.

For workbook imports, persist the **wrapper module path** from each sweep fixture (for example `example.com/rd-sim@v1.0.0`) as `kernel_revision`. Downstream dashboards group by wrapper name, not the replaced target.

See also `/app/workbook/kernels/kernel-registry.toml` for the promotion registry.
