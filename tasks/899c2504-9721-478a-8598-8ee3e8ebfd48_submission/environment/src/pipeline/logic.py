import hashlib

YES_TOKENS = {"yes", "true", "ready", "1", "y"}


def token_is_yes(value: str) -> bool:
    return value.strip().lower() in YES_TOKENS


def ownership_state(rows: list[dict]) -> dict[str, dict[str, str]]:
    return {r["path"]: {"owner": r["owner"], "group": r["group"], "mode": r["mode"]} for r in rows}


def drift(rows: list[dict], owner: str, group: str, mode: str) -> list[str]:
    out = []
    for r in rows:
        if r["owner"] != owner or r["group"] != group or r["mode"] != mode:
            out.append(r["path"])
    return out


def drift_details(rows: list[dict], owner: str, group: str, mode: str) -> list[dict]:
    expected = {"owner": owner, "group": group, "mode": mode}
    details = []
    for r in rows:
        mismatches = []
        if r["owner"] != owner:
            mismatches.append("owner")
        if r["group"] != group:
            mismatches.append("group")
        if r["mode"] != mode:
            mismatches.append("mode")
        if mismatches:
            details.append({
                "path": r["path"],
                "observed": {"owner": r["owner"], "group": r["group"], "mode": r["mode"]},
                "expected": expected,
                "mismatch_fields": mismatches,
            })
    return details


def restart_plan(
    services: list[dict],
    required_units: list[str],
    allowlist: set[str],
) -> tuple[list[str], list[str]]:
    svc_by_unit = {s["unit"]: s for s in services}
    gated = []
    blocked = []
    for unit in required_units:
        if unit not in allowlist or unit not in svc_by_unit:
            continue
        s = svc_by_unit[unit]
        if not token_is_yes(s["needs_restart"]):
            continue
        if token_is_yes(s["ready"]):
            gated.append(unit)
        else:
            blocked.append(unit)
    return gated, blocked


def is_idempotent(drift_count: int, blocked_count: int) -> bool:
    return drift_count == 0 and blocked_count == 0


def digest(summary: dict[str, int]) -> str:
    parts = [f"{k}:{summary[k]}" for k in sorted(summary)]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
