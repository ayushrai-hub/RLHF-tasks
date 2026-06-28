"""Deterministic generator of held-out schedules for the perturbation test.

Produces varied but valid-ish ledgers (multiple accounts, dates spanning a leap
year and non-leap years, CREDIT/DEBIT/FEE/INTEREST records with mostly-random
INTEREST amounts, plus some malformed rows). The reference decides the expected
report; a checker that hardcodes the bundled answer or skips the interest
computation diverges on these inputs.
"""
import random

TYPES = ["CREDIT", "DEBIT", "FEE", "INTEREST", "CREDIT", "DEBIT", "WIRE", ""]
CURS = ["USD", "EUR", "GBP", "JPY", "CHF", "CNY", ""]
GOOD_DATES = ["20240115", "20240228", "20240229", "20241220", "20241231",
              "20250101", "20250110", "20250228", "20250630", "20251231",
              "20260101", "20260301", "20260401", "20260531", "20260613"]
BAD_DATES = ["20260614", "20261301", "20260000", "20240230", "2026013", "zzzzzzzz"]
AMOUNTS = ["0.00", "0.01", "10.00", "100.00", "1000.00", "5000.00", "10000.00",
           "25.00", "30.00", "8.10", "57.42", "1.5", ".5", "5.", "-1.00", "x", "1000"]


def generate(seed):
    """Return a tab-separated schedule string for the given integer seed."""
    rng = random.Random(seed)
    rows = []
    pool = []
    for _ in range(rng.randint(2, 16)):
        if rng.random() < 0.05:
            n = rng.randint(1, 5)
            rows.append("\t".join([_rid(rng, pool), _acct(rng), rng.choice(GOOD_DATES)][:n]))
            continue
        tid = _rid(rng, pool)
        if tid not in pool:
            pool.append(tid)
        date = rng.choice(GOOD_DATES if rng.random() < 0.8 else BAD_DATES)
        rows.append("\t".join([tid, _acct(rng), date, rng.choice(AMOUNTS),
                               rng.choice(TYPES), rng.choice(CURS)]))
    return "\n".join(rows) + "\n"


def _rid(rng, pool):
    if rng.random() < 0.2 and pool:
        return rng.choice(pool)
    if rng.random() < 0.1:
        return "T" + str(rng.randint(0, 99999))
    return "T%09d" % rng.randint(0, 999999999)


def _acct(rng):
    if rng.random() < 0.12:
        return "AC%04d" % rng.randint(0, 99)
    return "AC%06d" % rng.randint(1, 4)
