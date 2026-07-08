"""ETL output file verification — checks content and format correctness.

Tests verify behavior — what the output contains — not how the agent produced it.
Multiple correct implementations should all pass these assertions.
"""

import csv
import re
from pathlib import Path

OUTPUT_DIR = Path("/app/output")

# ── Helpers ──────────────────────────────────────────────────────────────

def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return (reader.fieldnames or [], rows)


def _col(header: list[str], *keywords: str) -> str | None:
    return next(
        (c for c in header if all(kw.lower() in c.lower() for kw in keywords)),
        None,
    )


def _has_col(header: list[str], *keywords: str) -> bool:
    return _col(header, *keywords) is not None


def _first_bytes(path: Path, n: int = 3) -> bytes:
    with open(path, "rb") as f:
        return f.read(n)


def _first_line(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.readline()


# ── File existence ───────────────────────────────────────────────────────

def test_consolidated_sales_exists():
    """Consolidated sales output file was created."""
    assert (OUTPUT_DIR / "consolidated_sales.csv").is_file()


def test_product_summary_exists():
    """Product summary output file was created."""
    assert (OUTPUT_DIR / "product_summary.csv").is_file()


def test_regional_summary_exists():
    """Regional summary output file was created."""
    assert (OUTPUT_DIR / "regional_summary.csv").is_file()


def test_validation_report_exists():
    """Validation report output file was created."""
    assert (OUTPUT_DIR / "validation_report.csv").is_file()


# ── Format hygiene ───────────────────────────────────────────────────────

def test_no_output_file_has_bom():
    """No output file begins with a UTF-8 BOM."""
    for name in ("consolidated_sales.csv", "product_summary.csv",
                 "regional_summary.csv", "validation_report.csv"):
        raw = _first_bytes(OUTPUT_DIR / name, 3)
        assert raw != b"\xef\xbb\xbf", f"{name} contains UTF-8 BOM"


def test_all_outputs_are_comma_delimited():
    """All output files use comma as the field delimiter."""
    for name in ("consolidated_sales.csv", "product_summary.csv",
                 "regional_summary.csv", "validation_report.csv"):
        line = _first_line(OUTPUT_DIR / name)
        assert "," in line, f"{name} is not comma-delimited"
        assert "\t" not in line, f"{name} uses tab delimiter"
        assert ";" not in line, f"{name} uses semicolon delimiter"


def test_all_outputs_are_valid_utf8():
    """All output files contain valid UTF-8 encoded text."""
    for name in ("consolidated_sales.csv", "product_summary.csv",
                 "regional_summary.csv", "validation_report.csv"):
        with open(OUTPUT_DIR / name, "rb") as f:
            raw = f.read()
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as e:
            raise AssertionError(f"{name} is not valid UTF-8: {e}")


# ── Consolidated sales — structure ───────────────────────────────────────

def test_consolidated_sales_has_required_columns():
    """Consolidated sales has date, product, quantity, unit price, and line total columns."""
    header, _ = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    assert _has_col(header, "date"), f"No date column in {header}"
    assert _has_col(header, "product"), f"No product ID column in {header}"
    assert _has_col(header, "quantity"), f"No quantity column in {header}"
    assert _has_col(header, "price") or _has_col(header, "unit"), \
        f"No unit price column in {header}"
    assert _has_col(header, "amount") or _has_col(header, "total") or _has_col(header, "usd"), \
        f"No line total column in {header}"


def test_consolidated_sales_row_count():
    """Consolidated sales contains between 40 and 48 valid rows after filtering."""
    _, rows = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    assert 40 <= len(rows) <= 48, f"Expected 40-48 valid rows, got {len(rows)}"


def test_consolidated_sales_dates_are_iso_format():
    """All dates in consolidated sales use YYYY-MM-DD format."""
    header, rows = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    date_col = _col(header, "date")
    assert date_col is not None, "No date column found"
    iso = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for i, row in enumerate(rows):
        d = row.get(date_col, "")
        assert iso.match(d), f"Row {i}: date '{d}' is not YYYY-MM-DD"


def test_consolidated_sales_amounts_are_numeric():
    """All unit-price and line-total values are valid numbers."""
    header, rows = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    price_col = _col(header, "price", "usd") or _col(header, "unit", "usd") or _col(header, "price") or _col(header, "unit")
    amt_col = _col(header, "amount", "usd") or _col(header, "total", "usd") or _col(header, "amount") or _col(header, "total") or _col(header, "usd")
    assert price_col and amt_col, "Missing price or amount column"
    for i, row in enumerate(rows):
        for col, label in ((price_col, "unit price"), (amt_col, "line total")):
            try:
                float(row[col])
            except (ValueError, KeyError):
                raise AssertionError(f"Row {i}: {label} not numeric")


# ── Consolidated sales — data quality invariants ─────────────────────────

def test_consolidated_sales_no_negative_or_zero_quantity():
    """No row has a quantity ≤ 0."""
    header, rows = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    qty_col = _col(header, "quantity")
    assert qty_col, "No quantity column"
    for i, row in enumerate(rows):
        qty = int(row[qty_col])
        assert qty > 0, f"Row {i}: quantity {qty} is not positive"


def test_consolidated_sales_no_duplicate_transactions():
    """No two rows share the same date, product ID, and quantity."""
    header, rows = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    date_col = _col(header, "date")
    pid_col = _col(header, "product")
    qty_col = _col(header, "quantity")
    assert date_col and pid_col and qty_col
    seen = set()
    for i, row in enumerate(rows):
        key = (row[date_col], row[pid_col], row[qty_col])
        assert key not in seen, f"Row {i}: duplicate transaction {key}"
        seen.add(key)


def test_consolidated_sales_no_unrecognized_products():
    """No row references a product ID outside the valid catalog (P001–P009)."""
    header, rows = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    pid_col = _col(header, "product")
    assert pid_col
    valid = {f"P00{i}" for i in range(1, 10)}
    for i, row in enumerate(rows):
        assert row[pid_col] in valid, f"Row {i}: unrecognized product {row[pid_col]}"


def test_consolidated_sales_grand_total_reasonable():
    """Sum of line totals is a reasonable positive value."""
    header, rows = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    amt_col = _col(header, "amount") or _col(header, "total") or _col(header, "usd")
    assert amt_col
    grand_total = sum(float(r[amt_col]) for r in rows)
    assert grand_total > 50000, f"Grand total {grand_total:.2f} too low"
    assert grand_total < 130000, f"Grand total {grand_total:.2f} too high"


def test_exchange_rate_applied_correctly():
    """EUR transaction on 2024-01-15 uses the correct period rate (1.08)."""
    header, rows = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    date_col = _col(header, "date")
    pid_col = _col(header, "product")
    qty_col = _col(header, "quantity")
    price_col = _col(header, "price", "usd") or _col(header, "unit", "usd") or _col(header, "price") or _col(header, "unit")
    assert date_col and pid_col and qty_col and price_col
    # EU row: 2024-01-15, P001, qty=100, EUR 10.50 × rate 1.08 = USD 11.34
    match = [r for r in rows
             if r[date_col] == "2024-01-15" and r[pid_col] == "P001" and r[qty_col] == "100"]
    assert len(match) == 1, f"Expected 1 matching row, got {len(match)}"
    actual_price = float(match[0][price_col])
    assert abs(actual_price - 11.34) < 0.02, \
        f"Expected unit price ~11.34 USD, got {actual_price}"


def test_line_total_equals_qty_times_price():
    """Every row's line total equals quantity × unit price within rounding tolerance."""
    header, rows = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    qty_col = _col(header, "quantity")
    price_col = _col(header, "price", "usd") or _col(header, "unit", "usd") or _col(header, "price") or _col(header, "unit")
    amt_col = _col(header, "amount", "usd") or _col(header, "total", "usd") or _col(header, "amount") or _col(header, "total") or _col(header, "usd")
    assert qty_col and price_col and amt_col, "Missing required columns"
    for i, row in enumerate(rows):
        expected = float(row[qty_col]) * float(row[price_col])
        actual = float(row[amt_col])
        assert abs(actual - expected) < 0.05, \
            f"Row {i}: line total {actual} ≠ {row[qty_col]} × {row[price_col]} = {expected}"


# ── Anomaly report ───────────────────────────────────────────────────────

def test_anomaly_report_exists():
    """Anomaly report output file was created."""
    assert (OUTPUT_DIR / "anomaly_report.csv").is_file()


def test_anomaly_report_has_required_columns():
    """Anomaly report has product ID, source, row, price, median, and deviation columns."""
    h, _ = _read_csv(OUTPUT_DIR / "anomaly_report.csv")
    assert _has_col(h, "product"), f"No product column in {h}"
    assert _has_col(h, "source") or _has_col(h, "file"), "No source column"
    assert _has_col(h, "row", "number") or _has_col(h, "row", "num") or _has_col(h, "row") or _has_col(h, "line"), "No row column"
    assert _has_col(h, "price") or _has_col(h, "unit"), "No unit price column"
    assert _has_col(h, "median"), "No median column"
    assert _has_col(h, "deviation") or _has_col(h, "pct"), "No deviation column"


def test_anomaly_report_deviation_above_threshold():
    """All reported anomalies have absolute deviation above 30%."""
    _, rows = _read_csv(OUTPUT_DIR / "anomaly_report.csv")
    assert len(rows) >= 1, "Anomaly report is empty; data contains known anomalies"
    dc = _col(list(rows[0].keys()), "deviation") or _col(list(rows[0].keys()), "pct")
    assert dc, "No deviation column"
    for i, r in enumerate(rows):
        val = r[dc].strip().rstrip('%')
        assert abs(float(val)) > 30, f"Row {i}: |deviation| {r[dc]}% not >30%"


# ── Product summary ──────────────────────────────────────────────────────

def test_product_summary_has_required_columns():
    """Product summary has product ID, name, quantity, and revenue columns."""
    header, _ = _read_csv(OUTPUT_DIR / "product_summary.csv")
    assert _has_col(header, "product"), f"No product ID column in {header}"
    assert _has_col(header, "name"), f"No name column in {header}"
    assert _has_col(header, "qty") or _has_col(header, "quantity"), \
        f"No quantity column in {header}"
    assert _has_col(header, "amount") or _has_col(header, "revenue") or _has_col(header, "total"), \
        f"No revenue column in {header}"


def test_product_summary_row_count():
    """Product summary contains exactly 9 product rows (P001-P009 including products with zero sales)."""
    _, rows = _read_csv(OUTPUT_DIR / "product_summary.csv")
    assert len(rows) == 9, f"Expected 9 products, got {len(rows)}"


def test_product_summary_names_from_latest_catalog():
    """Product names come from the most recent catalog (v2 preferred over v1)."""
    _, rows = _read_csv(OUTPUT_DIR / "product_summary.csv")
    name_col = next((c for c in rows[0] if "name" in c.lower()), None)
    pid_col = _col(list(rows[0].keys()), "product")
    assert name_col and pid_col, "Missing name or product column"
    by_pid = {row[pid_col]: row[name_col] for row in rows}
    # v2 names take precedence; fall back to v1 where v2 is absent
    assert by_pid.get("P001") == "Widget A Pro", f"P001 name: {by_pid.get('P001')}"
    assert by_pid.get("P003") == "Gadget X v2", f"P003 name: {by_pid.get('P003')}"
    assert by_pid.get("P005") == "Kit Z Pro", f"P005 name: {by_pid.get('P005')}"
    assert by_pid.get("P007") == "Module Q", f"P007 name: {by_pid.get('P007')}"
    # Unchanged names
    assert by_pid.get("P002") == "Widget B", f"P002 name: {by_pid.get('P002')}"
    assert by_pid.get("P004") == "Tool Y", f"P004 name: {by_pid.get('P004')}"
    assert by_pid.get("P006") == "Supply W", f"P006 name: {by_pid.get('P006')}"


def test_product_summary_quantities_non_negative():
    """All product quantities are non-negative integers."""
    _, rows = _read_csv(OUTPUT_DIR / "product_summary.csv")
    nc = next((c for c in rows[0] if "name" in c.lower()), None)
    qc = _col(list(rows[0].keys()), "qty") or _col(list(rows[0].keys()), "quantity")
    assert nc and qc
    for r in rows:
        q = int(r[qc])
        assert q >= 0, f"{r[nc]}: negative qty {q}"


def test_product_summary_cross_validates():
    """Product summary revenue matches consolidated sales grouped by product."""
    _, cs = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    ca = _col(list(cs[0].keys()), "amount") or _col(list(cs[0].keys()), "total") or _col(list(cs[0].keys()), "usd")
    cp = _col(list(cs[0].keys()), "product")
    assert ca and cp
    cs_by_pid = {}
    for r in cs:
        cs_by_pid[r[cp]] = cs_by_pid.get(r[cp], 0.0) + float(r[ca])
    _, ps = _read_csv(OUTPUT_DIR / "product_summary.csv")
    pp = _col(list(ps[0].keys()), "product")
    pa = _col(list(ps[0].keys()), "amount") or _col(list(ps[0].keys()), "revenue") or _col(list(ps[0].keys()), "total")
    assert pp and pa
    for r in ps:
        pid = r[pp]
        ps_amt = float(r[pa])
        cs_amt = cs_by_pid.get(pid, 0.0)
        assert abs(ps_amt - cs_amt) < 0.05, f"{pid}: summary {ps_amt} != consolidated {cs_amt}"


# ── Regional summary ─────────────────────────────────────────────────────

def test_regional_summary_has_required_columns():
    """Regional summary has region, transaction count, and revenue columns."""
    header, _ = _read_csv(OUTPUT_DIR / "regional_summary.csv")
    assert _has_col(header, "region"), f"No region column in {header}"
    assert _has_col(header, "transaction") or _has_col(header, "count") or _has_col(header, "txn"), \
        f"No transaction count column in {header}"
    assert _has_col(header, "amount") or _has_col(header, "revenue") or _has_col(header, "total"), \
        f"No revenue column in {header}"


def test_regional_summary_row_count():
    """Regional summary contains exactly 8 region rows (one per source system)."""
    _, rows = _read_csv(OUTPUT_DIR / "regional_summary.csv")
    assert len(rows) == 8, f"Expected 8 regions, got {len(rows)}"


def test_regional_summary_cross_validates():
    """Regional summary revenue total matches consolidated sales total."""
    _, cs = _read_csv(OUTPUT_DIR / "consolidated_sales.csv")
    ca = _col(list(cs[0].keys()), "amount") or _col(list(cs[0].keys()), "total") or _col(list(cs[0].keys()), "usd")
    assert ca
    cs_total = sum(float(r[ca]) for r in cs)
    _, rs = _read_csv(OUTPUT_DIR / "regional_summary.csv")
    ra = _col(list(rs[0].keys()), "amount") or _col(list(rs[0].keys()), "revenue") or _col(list(rs[0].keys()), "total")
    assert ra
    rs_total = sum(float(r[ra]) for r in rs)
    assert abs(cs_total - rs_total) < 0.20, f"Regional {rs_total} != consolidated {cs_total}"


def test_regional_summary_transaction_count_positive():
    """Every region has a positive transaction count."""
    _, rows = _read_csv(OUTPUT_DIR / "regional_summary.csv")
    rc = _col(list(rows[0].keys()), "region")
    tc = _col(list(rows[0].keys()), "transaction") or _col(list(rows[0].keys()), "count") or _col(list(rows[0].keys()), "txn")
    assert rc and tc
    for r in rows:
        assert int(r[tc]) > 0, f"Region {r[rc]}: txns {r[tc]} not positive"


# ── Validation report ────────────────────────────────────────────────────

def test_validation_report_has_required_columns():
    """Validation report has source file, row number, and reason columns."""
    header, _ = _read_csv(OUTPUT_DIR / "validation_report.csv")
    assert _has_col(header, "source") or _has_col(header, "file"), \
        f"No source/file column in {header}"
    assert _has_col(header, "row", "number") or _has_col(header, "row", "num") or _has_col(header, "row") or _has_col(header, "line"), \
        f"No row/line column in {header}"
    assert _has_col(header, "reason"), f"No reason column in {header}"


def test_validation_report_row_count():
    """Validation report contains between 8 and 14 rejected rows."""
    _, rows = _read_csv(OUTPUT_DIR / "validation_report.csv")
    assert 8 <= len(rows) <= 14, f"Expected 8-14 rejected rows, got {len(rows)}"


def _tokenize(text: str) -> set[str]:
    """Split text into lowercase tokens on underscores, hyphens, spaces, and slashes."""
    return set(t for t in re.split(r'[_\-\s/]+', text.lower()) if t)


def test_validation_report_covers_all_rejection_types():
    """Validation report includes at least one instance of each rejection category."""
    _, rows = _read_csv(OUTPUT_DIR / "validation_report.csv")
    reason_col = _col(list(rows[0].keys()), "reason")
    assert reason_col, "No reason column"

    reasons_text = " ".join(r[reason_col].lower() for r in rows)
    tokens = set()
    for r in rows:
        tokens.update(_tokenize(r[reason_col]))

    def _has_any(*keywords: str) -> bool:
        return any(kw in reasons_text for kw in keywords) or bool(tokens & set(keywords))

    assert _has_any("negative", "zero", "neg", "quantity", "qty"), \
        f"Missing quantity rejection (negative/zero) in: {reasons_text[:200]}"
    assert _has_any("bad date", "unparseable", "malformed", "invalid", "date"), \
        f"Missing date rejection in: {reasons_text[:200]}"
    assert _has_any("duplicate", "dup", "already", "repeat"), \
        f"Missing duplicate rejection in: {reasons_text[:200]}"
    assert _has_any("unrecognized", "unknown", "catalog", "found", "product"), \
        f"Missing unrecognized product rejection in: {reasons_text[:200]}"
    assert _has_any("non-numeric", "nan", "n/a", "price", "numeric"), \
        f"Missing non-numeric value rejection in: {reasons_text[:200]}"


def test_validation_report_metadata_accurate():
    """Validation report source files and row numbers are present and consistent."""
    _, rows = _read_csv(OUTPUT_DIR / "validation_report.csv")
    src_col = _col(list(rows[0].keys()), "source") or _col(list(rows[0].keys()), "file")
    row_col = _col(list(rows[0].keys()), "row", "number") or _col(list(rows[0].keys()), "row", "num") or _col(list(rows[0].keys()), "row") or _col(list(rows[0].keys()), "line")
    reason_col = _col(list(rows[0].keys()), "reason")
    assert src_col and row_col and reason_col, "Missing required columns"

    # Verify each row has a valid source filename and positive row number
    for i, r in enumerate(rows):
        assert r[src_col].strip() != "", f"Row {i}: empty source file"
        assert int(r[row_col]) > 0, f"Row {i}: invalid row number {r[row_col]}"

    # Verify specific expected rejections exist with correct source file
    # Accept both bare region keys (EU) and filenames (sales_eu.csv)
    def _src_matches(src: str, region: str) -> bool:
        return region in src.upper()

    by_src = {}
    for r in rows:
        src = r[src_col].upper()
        by_src.setdefault(src, []).append(r[reason_col].lower())

    def _any_src(region: str, *keywords: str) -> bool:
        return any(_src_matches(k, region) and any(kw in v for kw in keywords)
                   for k, vv in by_src.items() for v in vv)

    assert _any_src("EU", "negative", "zero", "neg", "quantity", "qty"), "EU missing quantity rejection"
    assert _any_src("US", "duplicate", "dup", "already", "repeat"), "US missing duplicate rejection"
    assert _any_src("US", "invalid", "bad date", "unparseable", "malformed"), "US missing invalid date rejection"
    assert _any_src("APAC", "non-numeric", "nan", "n/a", "price", "numeric"), "APAC missing non-numeric price rejection"
    assert _any_src("UK", "invalid", "bad date", "unparseable", "malformed"), "UK missing invalid date rejection"
    assert _any_src("LATAM", "invalid", "bad date", "unparseable", "malformed"), "LATAM missing invalid date rejection"
    assert _any_src("LATAM", "unrecognized", "unknown", "catalog", "found", "product"), "LATAM missing unrecognized product rejection"


# ── Language constraint ──────────────────────────────────────────────────

def test_pipeline_is_php():
    """Pipeline is implemented in PHP as required by the instructions."""
    src = Path("/app/src")
    php_files = list(src.rglob("*.php"))
    assert len(php_files) >= 1, "No PHP files found in /app/src/; PHP 8.2+ pipeline required"
    total_lines = 0
    for f in php_files:
        total_lines += len(f.read_text(encoding="utf-8", errors="ignore").splitlines())
    assert total_lines >= 50, \
        f"PHP code too short ({total_lines} lines across {len(php_files)} file(s)); expected substantive pipeline"


# ── Anomaly spot-check ───────────────────────────────────────────────────

def test_anomaly_report_includes_known_outlier():
    """Anomaly report flags the known MEA P002 price outlier (~$200.50 vs median ~$25)."""
    _, rows = _read_csv(OUTPUT_DIR / "anomaly_report.csv")
    assert len(rows) >= 2, f"Expected at least 2 anomalies, got {len(rows)}"
    pid_col = _col(list(rows[0].keys()), "product")
    price_col = _col(rows[0].keys(), "price") or _col(rows[0].keys(), "unit")
    assert pid_col and price_col, "Missing product or price column in anomaly report"
    p002_rows = [r for r in rows if r[pid_col] == "P002" and float(r[price_col].strip().rstrip('%')) > 100]
    assert len(p002_rows) >= 1, "Missing MEA P002 high-price anomaly ($200.50)"

