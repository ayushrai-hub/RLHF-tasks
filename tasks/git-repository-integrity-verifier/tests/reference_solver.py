"""Reference solver for git-repository-integrity-verifier."""
from __future__ import annotations

import json
from pathlib import Path

DATA = Path("/app/data")


def load_json(name: str):
    with (DATA / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def round_metric(value: float, decimals: int) -> float:
    factor = 10**decimals
    return round(value * factor + 1e-9) / factor


def build_graph() -> dict[str, dict]:
    return {item["sha"]: item for item in load_json("commit_graph.json")["commits"]}


def ancestors(graph: dict[str, dict], sha: str) -> set[str]:
    seen: set[str] = set()
    stack = [sha]
    while stack:
        current = stack.pop()
        if current in seen or current not in graph:
            continue
        seen.add(current)
        stack.extend(graph[current]["parents"])
    return seen


def first_parent_ancestors(graph: dict[str, dict], sha: str) -> set[str]:
    seen: set[str] = set()
    current: str | None = sha
    while current and current not in seen and current in graph:
        seen.add(current)
        parents = graph[current]["parents"]
        current = parents[0] if parents else None
    return seen


def merge_base(graph: dict[str, dict], tip_a: str, tip_b: str) -> str | None:
    anc_a = ancestors(graph, tip_a)
    stack = [tip_b]
    seen: set[str] = set()
    candidates: list[str] = []
    while stack:
        current = stack.pop()
        if current in seen or current not in graph:
            continue
        seen.add(current)
        if current in anc_a:
            candidates.append(current)
        stack.extend(graph[current]["parents"])
    if not candidates:
        return None
    return max(candidates, key=lambda sha: len(ancestors(graph, sha)))


def count_ahead(graph: dict[str, dict], tip: str, base: str | None) -> int:
    if base is None:
        return len(ancestors(graph, tip))
    reachable = ancestors(graph, tip)
    base_anc = ancestors(graph, base)
    return len(reachable - base_anc)


def branch_tip_map() -> dict[str, str]:
    return {item["name"]: item["tip"] for item in load_json("branch_refs.json")["branches"]}


def selector_index(selector: str) -> int:
    start = selector.rfind("@{")
    end = selector.rfind("}")
    return int(selector[start + 2 : end])


def reason_from_message(message: str, policy: dict) -> str | None:
    lowered = message.lower()
    for rule in policy["orphan_classification"]["reflog_message_patterns"]:
        if rule["match_substring"] in lowered:
            return rule["reason"]
    return None


def classify_orphan(sha: str, pick_ref: str, reflog: list[dict], policy: dict) -> str:
    default = policy["orphan_classification"]["default_reason"]
    if policy["orphan_classification"].get("infer_supersession_from_same_ref"):
        ref_entries = [entry for entry in reflog if entry["ref"] == pick_ref]
        ref_entries.sort(key=lambda row: selector_index(row["selector"]))
        orphan_index = next(
            index for index, entry in enumerate(ref_entries) if entry["new_sha"] == sha
        )
        for newer in ref_entries[:orphan_index]:
            reason = reason_from_message(newer["message"], policy)
            if reason:
                return reason
    pick_message = next(entry["message"] for entry in reflog if entry["new_sha"] == sha and entry["ref"] == pick_ref)
    return reason_from_message(pick_message, policy) or default


def compute_orphans(graph: dict[str, dict], policy: dict, repo_id: str) -> dict:
    branches = branch_tip_map()
    tags = load_json("tag_history.json")["tags"]
    reflog = load_json("reflog_snapshots.json")["entries"]

    advertised: set[str] = set()
    for tip in branches.values():
        advertised |= ancestors(graph, tip)
    for tag in tags:
        advertised |= ancestors(graph, tag["peeled"])

    reflog_by_sha: dict[str, list[dict]] = {}
    for entry in reflog:
        reflog_by_sha.setdefault(entry["new_sha"], []).append(entry)

    orphans = []
    for sha in sorted(graph):
        if sha in advertised:
            continue
        entries = reflog_by_sha.get(sha)
        if not entries:
            continue
        pick = sorted(entries, key=lambda row: row["ref"])[0]
        orphans.append(
            {
                "sha": sha,
                "subject": graph[sha]["subject"],
                "orphan_reason": classify_orphan(sha, pick["ref"], reflog, policy),
                "discovered_via_ref": pick["ref"],
                "reflog_message": pick["message"],
            }
        )

    return {"repository_id": repo_id, "orphans": orphans, "count": len(orphans)}


def compute_branch_divergence(graph: dict[str, dict], policy: dict, repo_id: str) -> dict:
    branches = branch_tip_map()
    names = sorted(branches)
    pairs = []
    for index, branch_a in enumerate(names):
        for branch_b in names[index + 1 :]:
            tip_a = branches[branch_a]
            tip_b = branches[branch_b]
            base = merge_base(graph, tip_a, tip_b)
            ahead_a = count_ahead(graph, tip_a, base)
            ahead_b = count_ahead(graph, tip_b, base)
            pairs.append(
                {
                    "branch_a": branch_a,
                    "branch_b": branch_b,
                    "merge_base": base,
                    "ahead_a": ahead_a,
                    "ahead_b": ahead_b,
                    "divergence_total": ahead_a + ahead_b,
                }
            )
    return {"repository_id": repo_id, "pairs": pairs}


def compute_merge_consistency(graph: dict[str, dict], policy: dict, metadata: dict) -> tuple[float, list[str]]:
    merges = load_json("merge_commits.json")["merges"]
    if not merges:
        return float(policy["merge_consistency"]["empty_merges_score"]), []

    default_tip = branch_tip_map()[metadata["default_branch"]]
    fp_anc = first_parent_ancestors(graph, default_tip)
    findings: list[str] = []
    valid = 0
    required = policy["merge_consistency"]["required_parent_count"]

    for merge in merges:
        parents = merge["parents"]
        ok = len(parents) == required
        if policy["merge_consistency"]["require_parents_in_graph"]:
            ok = ok and all(parent in graph for parent in parents)
        if ok and parents:
            ok = parents[0] in fp_anc
        if ok:
            valid += 1
        else:
            findings.append(
                f"merge {merge['sha'][:7]} inconsistent: parents={len(parents)} "
                f"first_parent_on_mainline={parents[0] in fp_anc if parents else False}"
            )

    score = round_metric(100.0 * valid / len(merges), policy["metrics_round_decimals"])
    return score, findings


def compute_graph_integrity(graph: dict[str, dict], policy: dict) -> tuple[float, int]:
    branches = load_json("branch_refs.json")["branches"]
    tags = load_json("tag_history.json")["tags"]
    checks = 0
    passed = 0

    shas = set(graph)
    checks += 1
    passed += 1 if len(shas) == len(graph) else 0

    for commit in graph.values():
        for parent in commit["parents"]:
            checks += 1
            if parent in graph:
                passed += 1

    for branch in branches:
        checks += 1
        if branch["tip"] in graph:
            passed += 1

    for tag in tags:
        checks += 1
        if tag["peeled"] in graph:
            passed += 1

    score = round_metric(100.0 * passed / checks, policy["metrics_round_decimals"]) if checks else 100.0
    return score, checks


def compute_history_reconstruction(graph: dict[str, dict], policy: dict, repo_id: str) -> str:
    reflog = load_json("reflog_snapshots.json")["entries"]
    include_actions = policy["history_event_filter"]["include_reflog_actions"]
    exclude = policy["history_event_filter"]["exclude_substrings"]
    history_cfg = policy["outputs"]["history_reconstruction"]
    lines = [history_cfg["title_template"].format(repository_id=repo_id), ""]

    events = []
    for entry in reflog:
        message = entry["message"]
        if any(fragment in message for fragment in exclude):
            continue
        action = message.split(":", 1)[0].strip().lower()
        action = action.replace("commit (", "commit").replace(")", "")
        if not any(action.startswith(prefix) for prefix in include_actions):
            continue
        sha = entry["new_sha"]
        author_date = graph.get(sha, {}).get("author_date", "unknown")
        events.append(
            {
                "author_date": author_date,
                "ref": entry["ref"],
                "selector": entry["selector"],
                "summary": message,
            }
        )

    events.sort(key=lambda row: (row["author_date"], row["ref"], row["selector"]))
    template = history_cfg["line_template"]
    for event in events:
        lines.append(
            template.format(
                author_date=event["author_date"],
                ref=event["ref"],
                summary=event["summary"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def compute_integrity_report(
    repo_id: str,
    graph_score: float,
    merge_score: float,
    merge_findings: list[str],
    orphan_doc: dict,
    pair_count: int,
    policy: dict,
) -> str:
    report_cfg = policy["outputs"]["repository_integrity_report"]
    decimals = policy["metrics_round_decimals"]
    graph = build_graph()
    lines = [report_cfg["title_template"].format(repository_id=repo_id), ""]

    lines.extend(["## Repository Summary", ""])
    summary = report_cfg["repository_summary_lines"]
    lines.append(summary["repository_id"].format(repository_id=repo_id))
    lines.append(summary["commits_in_graph"].format(commit_count=len(graph)))
    lines.append(summary["active_branches"].format(branch_count=len(branch_tip_map())))
    lines.append("")

    lines.extend(["## Integrity Metrics", ""])
    metrics = report_cfg["metric_line_templates"]
    lines.append(metrics["graph_integrity_score"].format(value=round_metric(graph_score, decimals)))
    lines.append(metrics["merge_consistency_score"].format(value=round_metric(merge_score, decimals)))
    lines.append(metrics["orphan_commit_count"].format(count=orphan_doc["count"]))
    lines.append(metrics["branch_pair_count"].format(count=pair_count))
    lines.append("")

    lines.extend(["## Merge Findings", ""])
    if merge_findings:
        lines.extend(merge_findings)
    else:
        lines.append(report_cfg["merge_findings_clean_line"])
    lines.append("")

    lines.extend(["## Orphan Summary", ""])
    sha_len = report_cfg["sha_short_length"]
    orphan_template = report_cfg["orphan_entry_line_template"]
    if orphan_doc["orphans"]:
        for orphan in orphan_doc["orphans"]:
            lines.append(
                orphan_template.format(
                    sha_short=orphan["sha"][:sha_len],
                    subject=orphan["subject"],
                    orphan_reason=orphan["orphan_reason"],
                )
            )
    else:
        lines.append(report_cfg["orphan_no_orphans_line"])
    lines.append("")

    return "\n".join(lines)


def compute_expected() -> tuple[dict, dict, str, str]:
    policy = load_json("integrity_policy.json")
    metadata = load_json("repository_metadata.json")
    repo_id = metadata["repository_id"]
    graph = build_graph()

    orphan_doc = compute_orphans(graph, policy, repo_id)
    divergence_doc = compute_branch_divergence(graph, policy, repo_id)
    merge_score, merge_findings = compute_merge_consistency(graph, policy, metadata)
    graph_score, _ = compute_graph_integrity(graph, policy)

    report = compute_integrity_report(
        repo_id,
        graph_score,
        merge_score,
        merge_findings,
        orphan_doc,
        len(divergence_doc["pairs"]),
        policy,
    )
    history = compute_history_reconstruction(graph, policy, repo_id)
    return divergence_doc, orphan_doc, report, history
