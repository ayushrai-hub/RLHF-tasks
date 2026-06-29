"""Executable reference spec for accaudit-wren v6.

v6 changes vs v5:
  - the USD annual rate follows a published schedule (1000 bps before 2025-01-01,
    1200 bps on/after), so per-day accrual must pick the rate by the day's date as
    well as the day's days-in-year (Actual/Actual). Other currencies are flat.
  - normalize(report) drops the free-form `detail` field so the full-report and
    perturbation tests grade structure (account/code/txn + order), not wording.
"""

VALID_TYPES = ["CREDIT", "DEBIT", "FEE", "INTEREST"]
VALID_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF"]
DATE_CUTOFF = "20260613"
USD_RATE_CHANGE = "20250101"  # USD rate steps up on this date
FLAT_RATE_BPS = {"EUR": 800, "GBP": 900, "JPY": 500, "CHF": 600}


def rate_for(currency, date):
    """Annual interest rate in basis points for a currency on a given YYYYMMDD date."""
    if currency == "USD":
        return 1200 if date >= USD_RATE_CHANGE else 1000
    return FLAT_RATE_BPS[currency]


def _all_digits(s):
    return len(s) > 0 and all("0" <= c <= "9" for c in s)


def _is_decimal(s):
    if not s:
        return False
    dot = digit = False
    for c in s:
        if c == ".":
            if dot:
                return False
            dot = True
        elif "0" <= c <= "9":
            digit = True
        else:
            return False
    return digit


def _is_leap(y):
    return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)


def _days_in_year(y):
    return 366 if _is_leap(y) else 365


def _days_in_month(y, m):
    if m == 2:
        return 29 if _is_leap(y) else 28
    if m in (4, 6, 9, 11):
        return 30
    return 31


def _is_valid_date(s):
    if len(s) != 8 or not _all_digits(s):
        return False
    if s > DATE_CUTOFF:
        return False
    y, m, d = int(s[0:4]), int(s[4:6]), int(s[6:8])
    if m < 1 or m > 12:
        return False
    if d < 1 or d > _days_in_month(y, m):
        return False
    return True


def _cents(amount_str):
    if "." in amount_str:
        whole, frac = amount_str.split(".")
    else:
        whole, frac = amount_str, ""
    frac = (frac + "00")[:2]
    whole = whole or "0"
    return int(whole) * 100 + int(frac)


def _round_half_up(n, d):
    return (2 * n + d) // (2 * d)


def _accrue(balance_cents, currency, start, end):
    """Interest accrued on a constant balance over calendar days [start, end).

    Each day uses the rate in effect for the currency on that date and the
    days-in-year of that day's own year; per-day amounts are half-up rounded to
    cents and summed. No interest on a zero or negative balance.
    """
    if balance_cents <= 0 or start >= end:
        return 0
    y, m, d = int(start[0:4]), int(start[4:6]), int(start[6:8])
    total = 0
    cur = start
    while cur < end:
        rate = rate_for(currency, cur)
        total += _round_half_up(balance_cents * rate, 10000 * _days_in_year(y))
        d += 1
        if d > _days_in_month(y, m):
            d = 1
            m += 1
            if m > 12:
                m = 1
                y += 1
        cur = "%04d%02d%02d" % (y, m, d)
    return total


def audit(content):
    lines = content.split("\n")
    errors = []
    txn_seen = {}
    acct_txns = {}

    for raw in lines:
        line = raw.rstrip("\r")
        if not line:
            continue
        fields = line.split("\t")
        txn_id = fields[0] if len(fields) > 0 else "?"
        acct_id = fields[1] if len(fields) > 1 else "?"

        if len(fields) < 6:
            errors.append((txn_id, acct_id, "MISSING_FIELD",
                           "expected 6 fields, got %d" % len(fields)))
            continue

        date, amount_str, type_name, currency = fields[2], fields[3], fields[4], fields[5]

        txn_ok = len(txn_id) == 10 and txn_id[0] == "T" and _all_digits(txn_id[1:10])
        if not txn_ok:
            errors.append((txn_id, acct_id, "BAD_TXN_ID", "must be T followed by 9 digits"))

        acct_ok = len(acct_id) == 8 and acct_id[0:2] == "AC" and _all_digits(acct_id[2:8])
        if not acct_ok:
            errors.append((txn_id, acct_id, "BAD_ACCT_ID", "must be AC followed by 6 digits"))

        date_ok = _is_valid_date(date)
        if not date_ok:
            errors.append((txn_id, acct_id, "BAD_DATE", "invalid or future date"))

        amount_ok = _is_decimal(amount_str)
        if not amount_ok:
            errors.append((txn_id, acct_id, "BAD_AMOUNT", "must be a non-negative decimal"))

        type_ok = type_name in VALID_TYPES
        if not type_ok:
            errors.append((txn_id, acct_id, "BAD_TYPE",
                           "must be CREDIT, DEBIT, FEE, or INTEREST"))

        curr_ok = currency in VALID_CURRENCIES
        if not curr_ok:
            errors.append((txn_id, acct_id, "BAD_CURRENCY",
                           "must be USD, EUR, GBP, JPY, or CHF"))

        is_dup = txn_id in txn_seen
        if is_dup:
            errors.append((txn_id, acct_id, "DUPLICATE_TXN",
                           "transaction ID seen more than once"))
        else:
            txn_seen[txn_id] = True

        if type_ok and type_name == "FEE" and amount_ok and _cents(amount_str) > 2500:
            errors.append((txn_id, acct_id, "FEE_OVERCAP",
                           "fee amount %s exceeds the 25.00 cap" % amount_str))

        if (not is_dup) and txn_ok and acct_ok and date_ok and amount_ok and type_ok and curr_ok:
            acct_txns.setdefault(acct_id, []).append(
                {"txn_id": txn_id, "date": date, "cents": _cents(amount_str),
                 "type": type_name, "currency": currency})

    for acct_id in acct_txns:
        txns = sorted(acct_txns[acct_id], key=lambda t: (t["date"], t["txn_id"]))

        debit_dates = {}
        for t in txns:
            if t["type"] == "DEBIT":
                debit_dates.setdefault(t["date"], []).append(t["txn_id"])
        for d, ids in debit_dates.items():
            if len(ids) > 5:
                for tid in ids:
                    errors.append((tid, acct_id, "HIGH_VELOCITY",
                                   "more than 5 debit transactions on %s" % d))

        currency = txns[0]["currency"]
        balance = 0
        accrued = 0
        last_date = txns[0]["date"]
        for i, t in enumerate(txns):
            if i > 0:
                accrued += _accrue(balance, currency, last_date, t["date"])
                last_date = t["date"]
            typ = t["type"]
            if typ == "CREDIT":
                balance += t["cents"]
            elif typ == "INTEREST":
                if t["cents"] != accrued:
                    errors.append((t["txn_id"], acct_id, "BAD_INTEREST",
                                   "posted interest does not match the accrued amount"))
                accrued = 0
                balance += t["cents"]
            else:
                balance -= t["cents"]
                if balance < 0:
                    errors.append((t["txn_id"], acct_id, "OVERDRAFT",
                                   "running balance fell below zero"))

    errors.sort(key=lambda e: (e[1], e[2], e[0]))
    return [{"txn_id": a, "account_id": b, "error_code": c, "detail": d}
            for (a, b, c, d) in errors]


def normalize(report):
    """Structural view of a report for equality checks: (account_id, error_code,
    txn_id) tuples in report order. The free-form `detail` text is intentionally
    excluded — the spec leaves its wording to the implementer."""
    return [(e["account_id"], e["error_code"], e["txn_id"]) for e in report]


def accrued_at_interest_points(content):
    """Helper for fixture authoring: the accrued cents expected at each INTEREST txn."""
    seen = {}
    acct_txns = {}
    for raw in content.split("\n"):
        line = raw.rstrip("\r")
        if not line:
            continue
        f = line.split("\t")
        if len(f) < 6:
            continue
        tid, aid, date, amt, typ, cur = f[:6]
        if (len(tid) == 10 and tid[0] == "T" and _all_digits(tid[1:10])
                and len(aid) == 8 and aid[:2] == "AC" and _all_digits(aid[2:8])
                and _is_valid_date(date) and _is_decimal(amt) and typ in VALID_TYPES
                and cur in VALID_CURRENCIES and tid not in seen):
            seen[tid] = True
            acct_txns.setdefault(aid, []).append(
                {"txn_id": tid, "date": date, "cents": _cents(amt), "type": typ, "currency": cur})
    out = {}
    for aid, txns in acct_txns.items():
        txns = sorted(txns, key=lambda t: (t["date"], t["txn_id"]))
        currency = txns[0]["currency"]
        balance = accrued = 0
        last_date = txns[0]["date"]
        for i, t in enumerate(txns):
            if i > 0:
                accrued += _accrue(balance, currency, last_date, t["date"])
                last_date = t["date"]
            if t["type"] == "CREDIT":
                balance += t["cents"]
            elif t["type"] == "INTEREST":
                out[t["txn_id"]] = accrued
                accrued = 0
                balance += t["cents"]
            else:
                balance -= t["cents"]
    return out
