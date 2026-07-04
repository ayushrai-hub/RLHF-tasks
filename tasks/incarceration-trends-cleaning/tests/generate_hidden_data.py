import csv
import random
from pathlib import Path


STATES = Path("/app/environment/data/states")
SEED = 20260613
KEEP_FRACTION = 0.7
URB_P = 0.15  # casing/whitespace noise on the urbanicity label
P_REC = 0.020  # eligible county-years turned into a correction filing pair
P_URB = 0.030  # eligible counties given a minority of mislabelled years
MIN_URB_ROWS = 6

CARRIED = [
    "state",
    "county_name",
    "urbanicity",
    "region",
    "total_pop_15to64",
    "total_jail_pop",
    "total_prison_pop",
]
CANON = ["rural", "small/mid", "suburban", "urban"]


def _read(path):
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    return rows[0], rows[1:]


def _write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _fips5(raw):
    return "%05d" % int(round(float((raw or "").strip())))


def _num(x):
    s = (x or "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _trunc0(x):
    v = _num(x)
    return None if v is None else int(v)


def _fold(u):
    return (u or "").strip().lower()


def _stale_jail(orig_int):
    v = orig_int + 500 + (orig_int % 7) * 13 + 1
    return v + 1 if v == orig_int else v


def reconcile_to_true(header, rows):
    """Collapse each county-year to one true row (latest non-blank per field)."""
    idx = {c: header.index(c) for c in CARRIED}
    fi = header.index("fips")
    yi = header.index("year")
    groups = {}
    order = []
    for row in rows:
        key = (_fips5(row[fi]), row[yi].strip())
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    true_rows = []
    for key in order:
        grp = groups[key]
        base = list(grp[0])
        for c in CARRIED:
            ci = idx[c]
            val = ""
            for row in grp:
                if row[ci].strip() != "":
                    val = row[ci]
            base[ci] = val
        true_rows.append(base)
    return true_rows


def reinject(header, rows, rng):
    """Re-apply casing noise + correction filings + urbanicity drift."""
    fi = header.index("fips")
    yi = header.index("year")
    ui = header.index("urbanicity")
    ji = header.index("total_jail_pop")

    by_fips = {}
    for i, r in enumerate(rows):
        by_fips.setdefault(_fips5(r[fi]), []).append(i)

    drift = {}
    for _fips, idxs in by_fips.items():
        if len(idxs) < MIN_URB_ROWS or rng.random() >= P_URB:
            continue
        labels = {_fold(rows[i][ui]) for i in idxs}
        if len(labels) != 1:
            continue
        lbl = next(iter(labels))
        k = max(1, (len(idxs) - 1) // 3)
        other = [c for c in CANON if c != lbl]
        newlbl = rng.choice(other)
        for i in rng.sample(sorted(idxs), k):
            drift[i] = newlbl

    blank = [""] * len(header)
    out = []
    for i, r in enumerate(rows):
        r = list(r)
        if i not in drift and r[ui].strip() and rng.random() < URB_P:
            u = r[ui].strip()
            r[ui] = rng.choice(
                [
                    u.upper(),
                    u.capitalize(),
                    " " + u,
                    u + "  ",
                    "  " + u.upper() + " ",
                ]
            )
        if i in drift:
            r[ui] = drift[i]
        eligible = i not in drift and _trunc0(r[ji]) is not None
        if eligible and rng.random() < P_REC:
            orig_raw = r[ji]
            initial = list(r)
            initial[ji] = str(_stale_jail(_trunc0(r[ji])))
            correction = list(blank)
            correction[fi] = r[fi]
            correction[yi] = r[yi]
            correction[ji] = orig_raw
            out.append(initial)
            out.append(correction)
        else:
            out.append(r)
    return out


def main():
    rng = random.Random(SEED)
    for path in sorted(STATES.glob("*.csv")):
        header, rows = _read(path)
        true_rows = reconcile_to_true(header, rows)

        kept = [row for row in true_rows if rng.random() < KEEP_FRACTION]
        if not kept:
            kept = true_rows[:1]

        _write(path, header, reinject(header, kept, rng))


if __name__ == "__main__":
    main()
