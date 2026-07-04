# Fixtures

Sample data for exercising the pay CLI. None of these are loaded automatically;
use `scripts/seed_demo.sh` to apply them.

- `payroll.csv` - an `employee,gross,mandatory,kind,priority,cap` chart of
  sample employees and their garnishment orders. Amounts are integer cents,
  priority is the integer allocation rank (lower paid first), and cap is the
  per-order net target the gross-up solver aims to clear.

The CSV file includes a header row.
