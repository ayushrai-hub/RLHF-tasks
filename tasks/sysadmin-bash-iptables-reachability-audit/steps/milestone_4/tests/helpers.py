"""Shared verifier helpers for sysadmin-bash-iptables-reachability-audit."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

APP_ROOT = Path("/app")
RAW_DIR = APP_ROOT / "data" / "raw"
API_DATA_DIR = APP_ROOT / "api" / "data"
TARGET_CLASSIFICATION_PATH = APP_ROOT / "api" / "contracts" / "target_classification.tsv"
LOCAL_OVERRIDES_PATH = APP_ROOT / "api" / "contracts" / "local_policy_overrides.tsv"
PROBE_PACKETS_PATH = APP_ROOT / "api" / "contracts" / "probe_packets.tsv"
TRACE_REPORT_PATH = APP_ROOT / "reports" / "packet_traces.csv"
SCHEMA_PATH = APP_ROOT / "db" / "schema.sql"
APP_PY_PATH = APP_ROOT / "api" / "app.py"
NORMALIZED_PATH = APP_ROOT / "data" / "normalized_iptables.jsonl"
DB_PATH = APP_ROOT / "data" / "iptables_audit.db"
REPORT_PATH = APP_ROOT / "reports" / "iptables_audit.csv"

PROTECTED_FILE_HASHES: dict = {
    "api/app.py": "e8bab4a32fa52e201f433c95e21ec34f49157c264ad495540fbe8859367dd280",
    "api/data/iptables_snapshot.json": "64b71212d98320d25333907b0fdf35705a88e31cf5e54bbbe7273173a8dff77c",
    "api/contracts/target_classification.tsv": "2259802ab00773b0bbc01c180ae6baee40f44791c1b208ecb9fb8b816c88c9f0",
    "api/contracts/local_policy_overrides.tsv": "d536751140325a0e32327856783ae584901076ba5cdaf892bc7cdc43afed09b3",
    "db/schema.sql": "eb46995750d98ea38a8f3e4f7439e8f91ca25576a3a3ca1accfaaaa898a512c2",
    "api/contracts/probe_packets.tsv": "cef0a5a40b9c484bdf1082df896280bac58c86e04609e1642bd429ecbd14e92a",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_protected_files_unchanged() -> None:
    bad = []
    for rel, expected in PROTECTED_FILE_HASHES.items():
        if expected.startswith("__"):
            continue
        actual = sha256_file(APP_ROOT / rel)
        if actual != expected:
            bad.append(f"{rel}: expected {expected}, got {actual}")
    assert not bad, "Protected files were modified:\n  " + "\n  ".join(bad)


def load_local_policy_overrides() -> list[dict]:
    """List of (match_kind, match_value, forced_target_type) overrides."""
    out = []
    for line in LOCAL_OVERRIDES_PATH.read_text().splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        out.append({
            "match_kind": parts[0],
            "match_value": parts[1],
            "forced_target_type": parts[2],
        })
    return out


def _apply_overrides(target: str, target_args: str, base_type: str, overrides: list[dict]) -> str:
    """If any override matches this rule, force the target_type. Last override wins."""
    forced = base_type
    for o in overrides:
        if o["match_kind"] == "log_prefix_contains":
            if target == "LOG" and o["match_value"] in (target_args or ""):
                forced = o["forced_target_type"]
        elif o["match_kind"] == "target_args_contains":
            if o["match_value"] in (target_args or ""):
                forced = o["forced_target_type"]
    return forced


def load_target_classification() -> dict:
    out = {}
    for line in TARGET_CLASSIFICATION_PATH.read_text().splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        out[parts[0]] = parts[1]
    return out


def load_raw_snapshot() -> dict:
    with (API_DATA_DIR / "iptables_snapshot.json").open() as f:
        return json.load(f)


def expected_chain_records() -> list[dict]:
    snap = load_raw_snapshot()
    out = []
    for t in snap["tables"]:
        for c in t["chains"]:
            out.append({
                "record_type": "chain",
                "table_name": t["name"],
                "name": c["name"],
                "chain_kind": c["kind"],
                "default_policy": c["default_policy"],
                "packet_count": int(c["packet_count"]),
                "byte_count": int(c["byte_count"]),
            })
    return out


def expected_rule_records() -> list[dict]:
    snap = load_raw_snapshot()
    tmap = load_target_classification()
    overrides = load_local_policy_overrides()
    # User-defined chains scoped per table: (table, chain_name).
    user_chains_by_table: dict[str, set] = {}
    for t in snap["tables"]:
        user_chains_by_table[t["name"]] = {
            c["name"] for c in t["chains"] if c["kind"] == "user_defined"
        }
    out = []
    for t in snap["tables"]:
        for r in t["rules"]:
            matcher = (r.get("matcher_text") or "").strip()
            target = r["target"]
            target_args = r.get("target_args", "")
            jump_kind = r.get("jump_kind", "jump")
            if target in tmap:
                target_type = tmap[target]
            elif target in user_chains_by_table.get(t["name"], set()):
                target_type = "goto" if jump_kind == "goto" else "jump"
            else:
                target_type = "unknown"
            # Apply local policy overrides AFTER default classification.
            target_type = _apply_overrides(target, target_args, target_type, overrides)
            out.append({
                "record_type": "rule",
                "rule_id": f"{t['name']}.{r['chain']}:{r['position']}",
                "table_name": t["name"],
                "chain": r["chain"],
                "position": int(r["position"]),
                "target": target,
                "target_args": r.get("target_args", ""),
                "target_type": target_type,
                "matcher_csv": matcher,
                "is_unconditional": 1 if matcher == "" else 0,
                "packet_count": int(r["packet_count"]),
                "byte_count": int(r["byte_count"]),
            })
    return out


def expected_normalized_records() -> list[dict]:
    return expected_chain_records() + expected_rule_records()


def read_normalized_records() -> list[dict]:
    assert NORMALIZED_PATH.exists(), f"missing {NORMALIZED_PATH}"
    out = []
    with open(NORMALIZED_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def expected_chain_graph() -> list[tuple]:
    """One (from_table_name, from_chain, to_table_name, to_chain, via_rule_id) per control-transfer edge — both JUMP (-j) and GOTO (-g) transfer control into the target chain, so both produce an edge."""
    out = []
    for r in expected_rule_records():
        if r["target_type"] in ("jump", "goto"):
            out.append((r["table_name"], r["chain"], r["table_name"], r["target"], r["rule_id"]))
    return out


def expected_rule_audit() -> dict:
    """Per-rule reachability keyed by rule_id."""
    rules = expected_rule_records()
    # Group rules by (table, chain).
    by_table_chain: dict[tuple, list[dict]] = {}
    for r in rules:
        by_table_chain.setdefault((r["table_name"], r["chain"]), []).append(r)

    audit: dict = {}
    for (_tn, _ch), chain_rules in by_table_chain.items():
        chain_rules.sort(key=lambda r: r["position"])
        first_blocker_pos = None
        first_blocker_id = None
        for r in chain_rules:
            if first_blocker_pos is not None and r["position"] > first_blocker_pos:
                audit[r["rule_id"]] = {
                    "rule_id": r["rule_id"],
                    "is_reachable": 0,
                    "blocked_by_rule_id": first_blocker_id,
                }
            else:
                audit[r["rule_id"]] = {
                    "rule_id": r["rule_id"],
                    "is_reachable": 1,
                    "blocked_by_rule_id": "",
                }
            if (
                first_blocker_pos is None
                and r["is_unconditional"] == 1
                and r["target_type"] in ("terminal", "return", "goto")
            ):
                first_blocker_pos = r["position"]
                first_blocker_id = r["rule_id"]
    return audit


def expected_chain_audit() -> dict:
    """Per-chain effective_default_policy + is_dead_chain + is_effectively_dead_chain
    keyed by (table, name). is_effectively_dead_chain is computed as a FIXPOINT:
    a user chain is effectively dead iff every inbound chain_graph edge is either
    (a) from a rule that is itself unreachable, or (b) from a chain that is itself
    effectively dead. The transitive case requires iteration until no chain status
    changes.
    """
    snap = load_raw_snapshot()
    rules = expected_rule_records()
    graph = expected_chain_graph()
    rule_audit = expected_rule_audit()
    inbound = {(to_tn, to_ch) for (_, _, to_tn, to_ch, _) in graph}

    # Initial dead-chain via simple inbound presence.
    out: dict = {}
    for t in snap["tables"]:
        for c in t["chains"]:
            name = c["name"]
            tn = t["name"]
            kind = c["kind"]
            declared = c["default_policy"]
            if kind == "user_defined":
                effective = "return"
                is_dead = 0 if (tn, name) in inbound else 1
            else:
                has_uncond_preempt = any(
                    r["table_name"] == tn
                    and r["chain"] == name
                    and r["is_unconditional"] == 1
                    and r["target_type"] in ("terminal", "goto")
                    for r in rules
                )
                effective = "preempted" if has_uncond_preempt else declared
                is_dead = 0
            out[(tn, name)] = {
                "table_name": tn,
                "name": name,
                "chain_kind": kind,
                "default_policy": declared,
                "effective_default_policy": effective,
                "is_dead_chain": is_dead,
                "is_effectively_dead_chain": 0,
            }

    # Fixpoint computation of is_effectively_dead_chain. Builtin chains are
    # entry points and never effectively dead. A user chain is effectively
    # dead iff NO chain_graph edge into it originates from a rule that is both
    # (a) reachable per rule_audit AND (b) in a chain that is not itself
    # effectively dead. Iterate until no chain status changes.
    rule_by_id = {r["rule_id"]: r for r in rules}
    effectively_dead = {
        key: 1 for key, info in out.items() if info["chain_kind"] == "user_defined"
    }
    while True:
        changed = False
        for key in list(effectively_dead.keys()):
            tn, name = key
            has_live_inbound = False
            for (from_tn, from_ch, to_tn, to_ch, via_rule_id) in graph:
                if to_tn != tn or to_ch != name:
                    continue
                via_rule = rule_by_id.get(via_rule_id)
                if via_rule is None:
                    continue
                if rule_audit.get(via_rule_id, {}).get("is_reachable", 0) != 1:
                    continue
                source_key = (from_tn, from_ch)
                # The source chain is "live" if it's a builtin OR a user chain
                # that is not currently marked effectively dead.
                source_info = out.get(source_key)
                if source_info is None:
                    continue
                if source_info["chain_kind"] == "user_defined" and effectively_dead.get(source_key, 0) == 1:
                    continue
                has_live_inbound = True
                break
            new_val = 0 if has_live_inbound else 1
            if effectively_dead[key] != new_val:
                effectively_dead[key] = new_val
                changed = True
        if not changed:
            break

    for key, val in effectively_dead.items():
        out[key]["is_effectively_dead_chain"] = val
    return out


def expected_report_header() -> list[str]:
    return [
        "rule_id", "table_name", "chain", "position", "target", "target_type",
        "is_unconditional", "is_reachable", "blocked_by_rule_id", "packet_count",
    ]


def expected_report_rows() -> list[list[str]]:
    rules = expected_rule_records()
    audit = expected_rule_audit()
    rules.sort(key=lambda r: (r["table_name"], r["chain"], r["position"]))
    rows = []
    sum_uncond = sum_reach = sum_packets = 0
    for r in rules:
        a = audit[r["rule_id"]]
        rows.append([
            r["rule_id"], r["table_name"], r["chain"], str(r["position"]),
            r["target"], r["target_type"],
            str(r["is_unconditional"]),
            str(a["is_reachable"]),
            a["blocked_by_rule_id"],
            str(r["packet_count"]),
        ])
        sum_uncond += r["is_unconditional"]
        sum_reach += a["is_reachable"]
        sum_packets += r["packet_count"]
    rows.append([
        "TOTAL", "", "", "", "", "",
        str(sum_uncond), str(sum_reach), "", str(sum_packets),
    ])
    return rows


def load_probe_packets() -> list[dict]:
    """List of probe dicts. Comment lines and the header row are skipped."""
    out = []
    started = False
    for line in PROBE_PACKETS_PATH.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if not started:
            started = True
            continue
        parts = line.split("\t")
        if len(parts) < 8:
            continue
        out.append({
            "probe_id": parts[0], "entry_table": parts[1],
            "entry_chain": parts[2], "in_iface": parts[3],
            "out_iface": parts[4], "proto": parts[5],
            "dport": parts[6], "state": parts[7],
        })
    return out


def _matcher_matches(matcher_csv: str, probe: dict) -> bool:
    """Evaluate a rule matcher against a probe. Every clause must match.
    `-m limit` clauses and an empty matcher always match; a clause whose
    field the probe carries as '-' does not match."""
    m = matcher_csv.strip()
    if m == "":
        return True
    toks = m.split()
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == "-i":
            if probe["in_iface"] != toks[i + 1]:
                return False
            i += 2
        elif t == "-o":
            if probe["out_iface"] != toks[i + 1]:
                return False
            i += 2
        elif t == "-p":
            if probe["proto"] != toks[i + 1]:
                return False
            i += 2
        elif t == "--dport":
            if probe["dport"] != toks[i + 1]:
                return False
            i += 2
        elif t == "-m":
            mod = toks[i + 1]
            if mod in ("state", "conntrack"):
                # next is --state/--ctstate then the set
                states = set(toks[i + 3].split(","))
                if probe["state"] not in states:
                    return False
                i += 4
            elif mod == "limit":
                # rate limiting is non-deterministic: always match
                # skip the module and its --limit <val> pair when present
                i += 2
                while i < len(toks) and not toks[i].startswith("-p") \
                        and toks[i] not in ("-i", "-o", "--dport", "-m"):
                    # consume limit args like --limit 5/sec
                    if toks[i] == "--limit":
                        i += 2
                    else:
                        i += 1
            else:
                i += 2
        elif t == "--state" or t == "--ctstate":
            states = set(toks[i + 1].split(","))
            if probe["state"] not in states:
                return False
            i += 2
        elif t == "--limit":
            i += 2
        else:
            i += 1
    return True


def expected_packet_traces() -> dict:
    """Simulate every probe through the ruleset with a jump/goto call stack.
    Returns probe_id -> {final_verdict, decided_by, hop_count, path}."""
    rules = expected_rule_records()
    chains = {(c["table_name"], c["name"]): c for c in expected_chain_records()}
    rules_by_chain: dict = {}
    for r in rules:
        rules_by_chain.setdefault((r["table_name"], r["chain"]), []).append(r)
    for key in rules_by_chain:
        rules_by_chain[key].sort(key=lambda r: r["position"])

    def is_builtin(table, chain):
        c = chains.get((table, chain))
        return c is not None and c["chain_kind"] == "builtin"

    def default_policy(table, chain):
        return chains[(table, chain)]["default_policy"]

    out = {}
    for probe in load_probe_packets():
        table = probe["entry_table"]
        entry = probe["entry_chain"]
        chain, idx = entry, 0
        stack = []  # return frames: (chain, resume_index)
        path = []
        verdict = decided_by = None
        guard = 0
        while True:
            guard += 1
            if guard > 100000:
                verdict, decided_by = "LOOP", ""
                break
            rlist = rules_by_chain.get((table, chain), [])
            if idx >= len(rlist):
                # fell off the end of the chain
                if is_builtin(table, chain):
                    verdict = default_policy(table, chain)
                    decided_by = f"policy:{table}.{chain}"
                    break
                if stack:
                    chain, idx = stack.pop()
                    continue
                # returned past the entry built-in -> entry policy
                verdict = default_policy(table, entry)
                decided_by = f"policy:{table}.{entry}"
                break
            r = rlist[idx]
            if not _matcher_matches(r["matcher_csv"], probe):
                idx += 1
                continue
            path.append(r["rule_id"])
            tt = r["target_type"]
            if tt == "terminal":
                verdict, decided_by = r["target"], r["rule_id"]
                break
            if tt == "non_terminal":
                idx += 1
                continue
            if tt == "return":
                if is_builtin(table, chain):
                    verdict = default_policy(table, chain)
                    decided_by = f"policy:{table}.{chain}"
                    break
                if stack:
                    chain, idx = stack.pop()
                    continue
                verdict = default_policy(table, entry)
                decided_by = f"policy:{table}.{entry}"
                break
            if tt == "jump":
                stack.append((chain, idx + 1))
                chain, idx = r["target"], 0
                continue
            if tt == "goto":
                # goto installs no return frame: control inherits the
                # current chain's return target, so when the goto'd chain
                # returns/falls off it resumes the GRANDPARENT, not here.
                chain, idx = r["target"], 0
                continue
            # unknown target: no-op, continue
            idx += 1
        out[probe["probe_id"]] = {
            "final_verdict": verdict,
            "decided_by": decided_by,
            "hop_count": len(path),
            "path": "|".join(path),
        }
    return out


def expected_trace_header() -> list[str]:
    return ["probe_id", "entry_table", "entry_chain",
            "final_verdict", "decided_by", "hop_count", "path"]


def expected_trace_rows() -> list[list[str]]:
    probes = {p["probe_id"]: p for p in load_probe_packets()}
    traces = expected_packet_traces()
    rows = []
    total_hops = 0
    for pid in sorted(traces.keys()):
        t = traces[pid]
        p = probes[pid]
        rows.append([
            pid, p["entry_table"], p["entry_chain"],
            t["final_verdict"], t["decided_by"],
            str(t["hop_count"]), t["path"],
        ])
        total_hops += t["hop_count"]
    rows.append(["TOTAL", "", "", "", "", str(total_hops), ""])
    return rows


def read_trace_report() -> list[list[str]]:
    assert TRACE_REPORT_PATH.exists(), f"missing {TRACE_REPORT_PATH}"
    with open(TRACE_REPORT_PATH, newline="") as f:
        return list(csv.reader(f))


def read_report() -> list[list[str]]:
    assert REPORT_PATH.exists(), f"missing {REPORT_PATH}"
    with open(REPORT_PATH, newline="") as f:
        return list(csv.reader(f))
