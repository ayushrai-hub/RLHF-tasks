import hashlib
import json
import random
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

APP = Path("/app/task_file")
BIN = Path("/tmp/cookie-auditor")
PUBLIC_POLICY = APP / "input" / "policy.json"
PUBLIC_EVENTS = APP / "input" / "events.jsonl"
PUBLIC_HASHES = {
    "policy.json": "03ed03731600063485440d4b96bf207f134b4c58abaf4a219d55be5674bf0a9c",
    "events.jsonl": "28c7ff9415bc1b14ec562ac183c617ae0712702c5614613a0ac88b417f97169c",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def b_len(s):
    return len(s.encode("utf-8"))


def host(url):
    return (urlparse(url).hostname or "").lower()


def path_of(url):
    return urlparse(url).path or "/"


def scheme(url):
    return urlparse(url).scheme.lower()


def default_path(url):
    p = path_of(url)
    if not p.startswith("/"):
        return "/"
    idx = p.rfind("/")
    if idx <= 0:
        return "/"
    return p[:idx]


def domain_match(req_host, cookie_domain):
    req_host = req_host.lower()
    cookie_domain = cookie_domain.lower()
    return req_host == cookie_domain or req_host.endswith("." + cookie_domain)


def path_match(req_path, cookie_path):
    if req_path == cookie_path:
        return True
    if not req_path.startswith(cookie_path):
        return False
    return cookie_path.endswith("/") or req_path[len(cookie_path):].startswith("/")


def registrable_site(hostname, suffixes):
    h = hostname.strip(".").lower()
    labels = h.split(".")
    best = None
    for suffix in suffixes:
        s = suffix.lower()
        if h == s or h.endswith("." + s):
            if best is None or len(s.split(".")) > len(best.split(".")):
                best = s
    if best is None:
        return ".".join(labels[-2:]) if len(labels) >= 2 else h
    suffix_labels = best.split(".")
    if len(labels) <= len(suffix_labels):
        return h
    return ".".join(labels[-len(suffix_labels)-1:])


def parse_set_cookie(header):
    parts = [p.strip() for p in header.split(";")]
    if not parts or "=" not in parts[0]:
        return "", "", {}
    name, value = parts[0].split("=", 1)
    attrs = {}
    for attr in parts[1:]:
        if not attr:
            continue
        if "=" in attr:
            k, v = attr.split("=", 1)
            attrs[k.lower()] = v.strip()
        else:
            attrs[attr.lower()] = True
    return name.strip(), value.strip(), attrs


def public_suffix(domain, suffixes):
    return domain.lower().strip(".") in {s.lower() for s in suffixes}


def cookie_risks(cookie, patterns):
    risks = []
    if not cookie["host_only"]:
        risks.append("overbroad_domain")
    if not cookie["secure"]:
        risks.append("missing_secure")
    lower_name = cookie["name"].lower()
    if any(re.search(pattern, lower_name, re.I) for pattern in patterns) and not cookie["http_only"]:
        risks.append("missing_httponly")
    return risks


def cookie_key(cookie):
    return {"name": cookie["name"], "domain": cookie["domain"], "path": cookie["path"]}


def lifecycle_key(name, domain, path):
    return (name, domain, path)


def jar_snapshot(event_id, jar, patterns):
    risk_counts = {}
    host_only_count = 0
    secure_count = 0
    domain_cookie_count = 0
    for cookie in jar:
        if cookie["host_only"]:
            host_only_count += 1
        else:
            domain_cookie_count += 1
        if cookie["secure"]:
            secure_count += 1
        for risk in cookie_risks(cookie, patterns):
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
    return {
        "id": event_id,
        "stored_count": len(jar),
        "host_only_count": host_only_count,
        "domain_cookie_count": domain_cookie_count,
        "secure_count": secure_count,
        "jar_cookie_keys": [cookie_key(cookie) for cookie in jar],
        "risk_counts": dict(sorted(risk_counts.items())),
    }


def max_age_state(attrs):
    if "max-age" not in attrs:
        return "absent"
    try:
        return "delete" if int(str(attrs["max-age"])) <= 0 else "positive"
    except ValueError:
        return "invalid"


def reference(policy_path, events_path):
    policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
    suffixes = policy["public_suffixes"]
    patterns = policy["sensitive_name_patterns"]
    max_header = int(policy["max_cookie_header_bytes"])
    jar = []
    rejections = []
    response_reports = []
    request_reports = []
    accepted = rejected = deleted = 0
    truncated_requests = 0
    domain_sent = {}
    domain_blocked = {}
    request_diagnostics = []
    lifecycle = {}
    jar_snapshots = []
    set_cookie_audit = []

    def touch_lifecycle(name, domain, path, event_id):
        key = lifecycle_key(name, domain, path)
        row = lifecycle.setdefault(key, {
            "name": name,
            "domain": domain,
            "path": path,
            "accepted_count": 0,
            "replaced_count": 0,
            "deleted_count": 0,
            "sent_count": 0,
            "blocked_count": 0,
            "first_event_id": event_id,
            "last_event_id": event_id,
            "final_state": "absent",
        })
        row["last_event_id"] = event_id
        return row

    def reject(event_id, name, reason):
        nonlocal rejected
        rejected += 1
        rejections.append({"event_id": event_id, "name": name, "reason": reason})

    for event in read_jsonl(events_path):
        if event["type"] == "response":
            origin = host(event["url"])
            accepted_keys = []
            deleted_keys = []
            for header_index, header in enumerate(event.get("set_cookie", [])):
                name, value, attrs = parse_set_cookie(header)
                if not name:
                    set_cookie_audit.append({
                        "event_id": event["id"],
                        "index": header_index,
                        "name": "",
                        "domain": "",
                        "path": "",
                        "host_only": False,
                        "secure": False,
                        "http_only": False,
                        "same_site": "Lax",
                        "max_age_state": "absent",
                        "disposition": "rejected",
                        "reason": "empty_name",
                    })
                    reject(event["id"], name, "empty_name")
                    continue
                audit = {
                    "event_id": event["id"],
                    "index": header_index,
                    "name": name,
                    "domain": "",
                    "path": "",
                    "host_only": True,
                    "secure": "secure" in attrs,
                    "http_only": "httponly" in attrs,
                    "same_site": "Lax",
                    "max_age_state": max_age_state(attrs),
                    "disposition": "",
                    "reason": "",
                }
                audit_same_site = str(attrs.get("samesite", "Lax")).capitalize()
                if audit_same_site not in {"Strict", "Lax", "None"}:
                    audit_same_site = "Lax"
                audit["same_site"] = audit_same_site
                dom_attr = attrs.get("domain")
                host_only = dom_attr is None
                if host_only:
                    cookie_domain = origin
                else:
                    cookie_domain = str(dom_attr).lower().lstrip(".")
                    if public_suffix(cookie_domain, suffixes):
                        audit.update({"domain": cookie_domain, "host_only": False, "path": str(attrs.get("path", default_path(event["url"]))), "disposition": "rejected", "reason": "public_suffix_domain"})
                        set_cookie_audit.append(audit)
                        reject(event["id"], name, "public_suffix_domain")
                        continue
                    if not domain_match(origin, cookie_domain):
                        audit.update({"domain": cookie_domain, "host_only": False, "path": str(attrs.get("path", default_path(event["url"]))), "disposition": "rejected", "reason": "domain_not_suffix"})
                        set_cookie_audit.append(audit)
                        reject(event["id"], name, "domain_not_suffix")
                        continue
                cookie_path = str(attrs.get("path", default_path(event["url"])))
                secure = "secure" in attrs
                http_only = "httponly" in attrs
                same_site = str(attrs.get("samesite", "Lax")).capitalize()
                if same_site not in {"Strict", "Lax", "None"}:
                    same_site = "Lax"
                audit.update({
                    "domain": cookie_domain,
                    "path": cookie_path,
                    "host_only": host_only,
                    "secure": secure,
                    "http_only": http_only,
                    "same_site": same_site,
                })
                if same_site == "None" and not secure:
                    audit.update({"disposition": "rejected", "reason": "samesite_none_without_secure"})
                    set_cookie_audit.append(audit)
                    reject(event["id"], name, "samesite_none_without_secure")
                    continue
                if name.startswith("__Secure-") and not secure:
                    audit.update({"disposition": "rejected", "reason": "secure_prefix_without_secure"})
                    set_cookie_audit.append(audit)
                    reject(event["id"], name, "secure_prefix_without_secure")
                    continue
                if name.startswith("__Host-") and (not secure or not host_only or cookie_path != "/"):
                    audit.update({"disposition": "rejected", "reason": "host_prefix_invalid"})
                    set_cookie_audit.append(audit)
                    reject(event["id"], name, "host_prefix_invalid")
                    continue
                max_age = attrs.get("max-age")
                if max_age is not None:
                    try:
                        if int(str(max_age)) <= 0:
                            before = len(jar)
                            jar = [c for c in jar if not (c["name"] == name and c["domain"] == cookie_domain and c["path"] == cookie_path)]
                            if len(jar) != before:
                                deleted += 1
                                deleted_keys.append({"name": name, "domain": cookie_domain, "path": cookie_path})
                                touch_lifecycle(name, cookie_domain, cookie_path, event["id"])["deleted_count"] += 1
                                audit["disposition"] = "deleted"
                            else:
                                audit["disposition"] = "ignored_delete"
                            set_cookie_audit.append(audit)
                            continue
                    except ValueError:
                        pass
                before = len(jar)
                jar = [c for c in jar if not (c["name"] == name and c["domain"] == cookie_domain and c["path"] == cookie_path)]
                row = touch_lifecycle(name, cookie_domain, cookie_path, event["id"])
                if len(jar) != before:
                    row["replaced_count"] += 1
                row["accepted_count"] += 1
                jar.append({
                    "name": name,
                    "value": value,
                    "domain": cookie_domain,
                    "path": cookie_path,
                    "host_only": host_only,
                    "secure": secure,
                    "http_only": http_only,
                    "same_site": same_site,
                })
                accepted_keys.append({"name": name, "domain": cookie_domain, "path": cookie_path})
                accepted += 1
                audit["disposition"] = "accepted"
                set_cookie_audit.append(audit)
            response_reports.append({"id": event["id"], "accepted_cookie_keys": accepted_keys, "deleted_cookie_keys": deleted_keys})
            jar_snapshots.append(jar_snapshot(event["id"], jar, patterns))
        elif event["type"] == "request":
            req_host = host(event["url"])
            req_path = path_of(event["url"])
            req_site = registrable_site(req_host, suffixes)
            top_site = event["top_level_site"].lower()
            same_site_req = req_site == top_site
            sent = []
            sent_details = []
            header_pairs = []
            blocked = []
            blocked_details = []
            eligible_cookie_keys = []
            blocked_reason_counts = {}
            header_limit_bytes_skipped = 0
            header_bytes = 0
            truncated = False
            for cookie in jar:
                reason = None
                if cookie["host_only"] and cookie["domain"] != req_host:
                    reason = "domain_mismatch"
                elif not cookie["host_only"] and not domain_match(req_host, cookie["domain"]):
                    reason = "domain_mismatch"
                elif not path_match(req_path, cookie["path"]):
                    reason = "path_mismatch"
                elif cookie["secure"] and scheme(event["url"]) != "https":
                    reason = "secure_only"
                elif cookie["same_site"] == "Strict" and not same_site_req:
                    reason = "samesite_strict"
                elif cookie["same_site"] == "Lax" and not (same_site_req or (event["is_top_level_navigation"] and event["method"].upper() == "GET")):
                    reason = "samesite_lax"
                if reason is None:
                    eligible_cookie_keys.append(cookie_key(cookie))
                    pair = f"{cookie['name']}={cookie['value']}"
                    pair_len = b_len(pair)
                    next_len = pair_len if not sent else header_bytes + 2 + pair_len
                    if next_len > max_header:
                        reason = "header_limit"
                        truncated = True
                        header_limit_bytes_skipped += pair_len
                    else:
                        sent.append(cookie["name"])
                        sent_details.append(cookie_key(cookie))
                        header_pairs.append(pair)
                        header_bytes = next_len
                        domain_sent[cookie["domain"]] = domain_sent.get(cookie["domain"], 0) + 1
                        touch_lifecycle(cookie["name"], cookie["domain"], cookie["path"], event["id"])["sent_count"] += 1
                if reason is not None:
                    blocked.append({"name": cookie["name"], "reason": reason})
                    blocked_details.append({"name": cookie["name"], "domain": cookie["domain"], "path": cookie["path"], "reason": reason})
                    domain_blocked[cookie["domain"]] = domain_blocked.get(cookie["domain"], 0) + 1
                    blocked_reason_counts[reason] = blocked_reason_counts.get(reason, 0) + 1
                    touch_lifecycle(cookie["name"], cookie["domain"], cookie["path"], event["id"])["blocked_count"] += 1
            if truncated:
                truncated_requests += 1
            request_reports.append({
                "id": event["id"],
                "sent_cookies": sent,
                "sent_cookie_keys": sent_details,
                "blocked_cookies": blocked,
                "blocked_cookie_keys": blocked_details,
                "cookie_header": "; ".join(header_pairs),
                "header_bytes": header_bytes,
            })
            request_diagnostics.append({
                "id": event["id"],
                "registrable_site": req_site,
                "top_level_site": top_site,
                "same_site_context": same_site_req,
                "eligible_cookie_keys": eligible_cookie_keys,
                "sent_cookie_keys": sent_details,
                "blocked_reason_counts": dict(sorted(blocked_reason_counts.items())),
                "header_limit_bytes_skipped": header_limit_bytes_skipped,
            })

    stored = []
    domain_stats = {}
    risk_counts = {}
    for cookie in jar:
        risks = cookie_risks(cookie, patterns)
        for risk in risks:
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        stats = domain_stats.setdefault(cookie["domain"], {
            "stored_cookie_count": 0,
            "host_only_cookie_count": 0,
            "secure_cookie_count": 0,
            "risk_counts": {},
        })
        stats["stored_cookie_count"] += 1
        if cookie["host_only"]:
            stats["host_only_cookie_count"] += 1
        if cookie["secure"]:
            stats["secure_cookie_count"] += 1
        for risk in risks:
            stats["risk_counts"][risk] = stats["risk_counts"].get(risk, 0) + 1
        stored.append({
            "name": cookie["name"],
            "domain": cookie["domain"],
            "path": cookie["path"],
            "host_only": cookie["host_only"],
            "secure": cookie["secure"],
            "http_only": cookie["http_only"],
            "same_site": cookie["same_site"],
            "risks": risks,
        })
    final_keys = {lifecycle_key(cookie["name"], cookie["domain"], cookie["path"]) for cookie in jar}
    lifecycle_rows = []
    for key in sorted(lifecycle, key=lambda item: (item[1], item[2], item[0])):
        row = dict(lifecycle[key])
        row["final_state"] = "stored" if key in final_keys else "absent"
        lifecycle_rows.append(row)
    domains = set(domain_stats) | set(domain_sent) | set(domain_blocked)
    domain_diagnostics = []
    for domain in sorted(domains):
        stats = domain_stats.get(domain, {
            "stored_cookie_count": 0,
            "host_only_cookie_count": 0,
            "secure_cookie_count": 0,
            "risk_counts": {},
        })
        domain_diagnostics.append({
            "domain": domain,
            "stored_cookie_count": stats["stored_cookie_count"],
            "host_only_cookie_count": stats["host_only_cookie_count"],
            "secure_cookie_count": stats["secure_cookie_count"],
            "sent_count": domain_sent.get(domain, 0),
            "blocked_count": domain_blocked.get(domain, 0),
            "risk_counts": dict(sorted(stats["risk_counts"].items())),
        })
    return {
        "summary": {
            "accepted": accepted,
            "set_cookie_rejected": rejected,
            "deleted": deleted,
            "request_count": len(request_reports),
            "risk_counts": dict(sorted(risk_counts.items())),
            "truncated_requests": truncated_requests,
        },
        "responses": response_reports,
        "set_cookie_audit": set_cookie_audit,
        "requests": request_reports,
        "rejections": rejections,
        "domain_diagnostics": domain_diagnostics,
        "request_diagnostics": request_diagnostics,
        "cookie_lifecycle": lifecycle_rows,
        "jar_snapshots": jar_snapshots,
        "stored_cookies": stored,
    }


def assert_equal(actual, expected, path="root"):
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path}: expected object"
        assert set(actual) == set(expected), f"{path}: expected keys {set(expected)}, got {set(actual)}"
        for key in expected:
            assert_equal(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list), f"{path}: expected list"
        assert len(actual) == len(expected), f"{path}: expected {len(expected)} items, got {len(actual)}"
        for i, (a, e) in enumerate(zip(actual, expected)):
            assert_equal(a, e, f"{path}[{i}]")
    else:
        assert actual == expected, f"{path}: expected {expected!r}, got {actual!r}"


_built = False


def build():
    global _built
    if not _built:
        proc = subprocess.run(["go", "build", "-o", str(BIN), "."], cwd=APP, capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, f"go build failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        _built = True


def run_auditor(policy, events, timeout=30):
    build()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "report.json"
        proc = subprocess.run(
            [str(BIN), "--policy", str(policy), "--events", str(events), "--output", str(out)],
            cwd=APP,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        assert proc.returncode == 0, f"auditor exited {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        assert out.exists(), "report file was not created"
        return json.loads(out.read_text(encoding="utf-8"))


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def write_policy(path, max_bytes=80):
    path.write_text(json.dumps({
        "public_suffixes": ["com", "net", "org", "co.uk", "internal"],
        "sensitive_name_patterns": ["session", "sid", "auth", "token"],
        "max_cookie_header_bytes": max_bytes,
    }), encoding="utf-8")


def test_public_inputs_are_unchanged():
    """Verify the sample policy and event fixtures were not modified."""
    assert sha256(PUBLIC_POLICY) == PUBLIC_HASHES["policy.json"], "input/policy.json was modified"
    assert sha256(PUBLIC_EVENTS) == PUBLIC_HASHES["events.jsonl"], "input/events.jsonl was modified"


def test_builds_with_documented_command():
    """Verify the Go CLI builds with the documented go build command."""
    build()


def test_solution_does_not_use_shortcuts_or_embed_fixtures():
    """Verify the implementation does not shell out to tests or embed fixture answers."""
    source = (APP / "main.go").read_text(encoding="utf-8").lower()
    forbidden = [
        "os/exec",
        "exec.command",
        "/tests",
        "test_outputs.py",
        "python",
        "public_audit_report_matches_reference",
        "28c7ff9415bc1b14ec562ac183c617ae0712702c5614613a0ac88b417f97169c",
    ]
    for token in forbidden:
        assert token not in source, f"solution source must not use shortcut token {token!r}"
    assert len(source.encode("utf-8")) <= 250_000, "main.go is too large; do not embed fixtures or outputs"


def test_public_audit_report_matches_reference():
    """Verify the public audit report matches the reference model exactly."""
    assert_equal(run_auditor(PUBLIC_POLICY, PUBLIC_EVENTS), reference(PUBLIC_POLICY, PUBLIC_EVENTS))


def test_prefix_deletion_default_path_and_samesite_edges(tmp_path):
    """Verify prefix rules, default paths, deletions, and SameSite behavior interact correctly."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=36)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/a/b/login", "set_cookie": [
            "sid=one; HttpOnly",
            "__Host-good=h; Path=/; Secure; SameSite=Strict",
            "__Host-bad=h; Domain=example.com; Path=/; Secure",
            "__Secure-ok=s; Secure; Path=/a",
            "cross=n; SameSite=None; Secure",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/a/b/panel", "method": "POST", "top_level_site": "attacker.net", "is_top_level_navigation": False},
        {"type": "response", "id": "r2", "url": "https://app.example.com/a/b/logout", "set_cookie": ["sid=gone; Path=/a/b; Max-Age=0"]},
        {"type": "request", "id": "q2", "url": "https://app.example.com/a/b/panel", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert any(r["reason"] == "host_prefix_invalid" for r in actual["rejections"])
    assert actual["summary"]["deleted"] == 1


def test_generated_large_log_is_data_driven(tmp_path):
    """Verify a larger varied event log is simulated rather than hardcoded."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=96)
    rows = []
    domains = ["alpha.example.com", "beta.example.com", "shop.service.co.uk", "api.service.co.uk"]
    for i in range(180):
        d = domains[i % len(domains)]
        base = "service.co.uk" if d.endswith("service.co.uk") else "example.com"
        rows.append({"type": "response", "id": f"r{i:03d}", "url": f"https://{d}/area/{i}/set", "set_cookie": [
            f"sess{i}=v{i}; Domain=.{base}; Path=/; Secure; HttpOnly; SameSite=Lax",
            f"pref{i}=p{i}; Path=/area/{i}; SameSite=Strict",
            f"tok{i}=t{i}; Path=/; SameSite=None; Secure" if i % 5 else f"bad{i}=x; Domain=.com",
        ]})
        method = "GET" if i % 3 else "POST"
        rows.append({"type": "request", "id": f"q{i:03d}", "url": f"https://{d}/area/{i}/view", "method": method, "top_level_site": base if i % 4 else "attacker.net", "is_top_level_navigation": i % 2 == 0})
        if i % 17 == 0:
            rows.append({"type": "response", "id": f"d{i:03d}", "url": f"https://{d}/area/{i}/clear", "set_cookie": [f"pref{i}=gone; Path=/area/{i}; Max-Age=0"]})
    write_jsonl(events, rows)
    assert_equal(run_auditor(policy, events, timeout=20), reference(policy, events))


def test_rejection_priority_and_attribute_normalization(tmp_path):
    """Verify rejection priority and case-insensitive attribute parsing."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    policy.write_text(json.dumps({
        "public_suffixes": ["com", "example", "co.uk", "uk"],
        "sensitive_name_patterns": ["session", "sid", "auth", "token"],
        "max_cookie_header_bytes": 120,
    }), encoding="utf-8")
    rows = [
        {"type": "response", "id": "r1", "url": "https://shop.example.com/login", "set_cookie": [
            "=empty; Domain=.com; Secure",
            "__Host-ps=1; Domain=.com; SameSite=None",
            "__Secure-cross=1; Domain=.evil.net; SameSite=None",
            "nonebad=1; SameSite=None",
            "__Secure-nope=1; Path=/secure",
            "__Host-nope=1; Domain=.example.com; Path=/; Secure",
            "SessionID=abc; PATH=/; secure; httponly; samesite=strict",
            "odd=1; SameSite=Unexpected; Path=/",
        ]},
        {"type": "request", "id": "q1", "url": "https://shop.example.com/", "method": "POST", "top_level_site": "attacker.com", "is_top_level_navigation": False},
        {"type": "request", "id": "q2", "url": "https://shop.example.com/", "method": "GET", "top_level_site": "attacker.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert [r["reason"] for r in actual["rejections"]] == [
        "empty_name",
        "public_suffix_domain",
        "domain_not_suffix",
        "samesite_none_without_secure",
        "secure_prefix_without_secure",
        "host_prefix_invalid",
    ]
    assert actual["requests"][0]["blocked_cookies"][-1] == {"name": "odd", "reason": "samesite_lax"}
    assert "odd" in actual["requests"][1]["sent_cookies"]


def test_replacement_order_deletion_keys_and_header_limit(tmp_path):
    """Verify replacement order, exact deletion keys, and greedy header-limit blocking."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=31)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/a/b/start", "set_cookie": [
            "a=11111; Path=/a; Secure; HttpOnly",
            "b=22222; Path=/a; Secure; HttpOnly",
            "c=33333; Path=/a; Secure; HttpOnly",
            "sid=old; Path=/a/b; Secure; HttpOnly",
        ]},
        {"type": "response", "id": "r2", "url": "https://app.example.com/a/b/next", "set_cookie": [
            "b=NEW22; Path=/a; Secure; HttpOnly",
            "sid=wrong; Path=/a; Max-Age=0",
            "sid=gone; Path=/a/b; Max-Age=0",
            "sid=gone-again; Path=/a/b; Max-Age=0",
            "d=44444; Domain=.example.com; Path=/a; Secure",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/a/b/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q2", "url": "https://other.example.com/a/b/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["summary"]["deleted"] == 1
    assert actual["summary"]["truncated_requests"] >= 1
    assert any(d["domain"] == "example.com" and d["blocked_count"] >= 1 for d in actual["domain_diagnostics"])
    assert actual["requests"][0]["sent_cookies"] == ["a", "c", "b"]
    assert actual["requests"][0]["cookie_header"] == "a=11111; c=33333; b=NEW22"
    assert actual["requests"][0]["header_bytes"] == len(actual["requests"][0]["cookie_header"])
    assert {"name": "d", "reason": "header_limit"} in actual["requests"][0]["blocked_cookies"]
    assert {"name": "a", "reason": "domain_mismatch"} in actual["requests"][1]["blocked_cookies"]
    q1_diag = next(row for row in actual["request_diagnostics"] if row["id"] == "q1")
    assert {"name": "d", "domain": "example.com", "path": "/a"} in q1_diag["eligible_cookie_keys"]
    assert q1_diag["blocked_reason_counts"]["header_limit"] == 1
    lifecycle = {(row["name"], row["domain"], row["path"]): row for row in actual["cookie_lifecycle"]}
    assert lifecycle[("b", "app.example.com", "/a")]["replaced_count"] == 1
    assert lifecycle[("sid", "app.example.com", "/a/b")]["deleted_count"] == 1
    assert lifecycle[("sid", "app.example.com", "/a/b")]["final_state"] == "absent"
    snapshots = {row["id"]: row for row in actual["jar_snapshots"]}
    assert snapshots["r2"]["jar_cookie_keys"] == [
        {"name": "a", "domain": "app.example.com", "path": "/a"},
        {"name": "c", "domain": "app.example.com", "path": "/a"},
        {"name": "b", "domain": "app.example.com", "path": "/a"},
        {"name": "d", "domain": "example.com", "path": "/a"},
    ]
    assert snapshots["r2"]["stored_count"] == 4


def test_overlapping_public_suffixes_and_samesite_site_calculation(tmp_path):
    """Verify longest public-suffix selection and SameSite site comparisons."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    policy.write_text(json.dumps({
        "public_suffixes": ["uk", "co.uk", "internal"],
        "sensitive_name_patterns": ["session", "sid", "auth", "token"],
        "max_cookie_header_bytes": 200,
    }), encoding="utf-8")
    rows = [
        {"type": "response", "id": "r1", "url": "https://shop.service.co.uk/a/set", "set_cookie": [
            "wide=1; Domain=.service.co.uk; Path=/; Secure; SameSite=Strict",
            "host=1; Path=/a; Secure; SameSite=Lax",
            "badps=1; Domain=.co.uk; Secure",
            "api=1; Domain=.api.service.co.uk; Secure",
        ]},
        {"type": "request", "id": "same-site", "url": "https://api.service.co.uk/a/check", "method": "POST", "top_level_site": "service.co.uk", "is_top_level_navigation": False},
        {"type": "request", "id": "cross-site-get", "url": "https://shop.service.co.uk/a/check", "method": "GET", "top_level_site": "other.co.uk", "is_top_level_navigation": True},
        {"type": "request", "id": "cross-site-post", "url": "https://shop.service.co.uk/a/check", "method": "POST", "top_level_site": "other.co.uk", "is_top_level_navigation": False},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert any(r["reason"] == "public_suffix_domain" for r in actual["rejections"])
    assert "wide" in actual["requests"][0]["sent_cookies"]
    assert {"name": "wide", "reason": "samesite_strict"} in actual["requests"][1]["blocked_cookies"]
    assert {"name": "host", "reason": "samesite_lax"} in actual["requests"][2]["blocked_cookies"]


def test_path_boundaries_default_paths_and_risk_counts(tmp_path):
    """Verify path matching boundaries, default paths, and stored-cookie risk counts."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=180)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/dir/login", "set_cookie": [
            "token=abc; Path=/dir; Secure",
            "session=abc; Path=/directory; HttpOnly",
            "plain=abc; Domain=.example.com; Path=/dir",
            "defaulted=abc; HttpOnly",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/dir2/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q2", "url": "https://app.example.com/dir/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q3", "url": "http://app.example.com/dir/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["sent_cookies"] == []
    assert {"name": "token", "reason": "secure_only"} in actual["requests"][2]["blocked_cookies"]
    assert actual["summary"]["risk_counts"] == expected["summary"]["risk_counts"]
    assert actual["domain_diagnostics"] == expected["domain_diagnostics"]
    assert actual["summary"]["risk_counts"]["missing_httponly"] >= 1


def test_duplicate_attributes_invalid_max_age_and_empty_headers(tmp_path):
    """Verify duplicate attributes, invalid Max-Age, empty headers, and deletion handling."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=120)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/root/start", "set_cookie": [
            "   ",
            "noval",
            "dup=one; Path=/wrong; Path=/root; SameSite=Strict; SameSite=None; Secure",
            "age=keep; Path=/root; Max-Age=not-an-int; HttpOnly",
            "gone=old; Path=/root; Secure",
            "gone=delete; Path=/root; Max-Age=-5",
            "gone=delete-again; Path=/root; Max-Age=0",
            "case=v; DOMAIN=.Example.COM; PATH=/root; secure; HTTPONLY; samesite=lax",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/root/page", "method": "POST", "top_level_site": "attacker.net", "is_top_level_navigation": False},
        {"type": "request", "id": "q2", "url": "https://app.example.com/root/page", "method": "GET", "top_level_site": "attacker.net", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert [r["reason"] for r in actual["rejections"]] == ["empty_name", "empty_name"]
    assert actual["summary"]["deleted"] == 1
    assert actual["responses"][0]["deleted_cookie_keys"] == [{"name": "gone", "domain": "app.example.com", "path": "/root"}]
    assert {"name": "case", "domain": "example.com", "path": "/root"} in actual["responses"][0]["accepted_cookie_keys"]
    stored = {c["name"]: c for c in actual["stored_cookies"]}
    assert stored["dup"]["path"] == "/root"
    assert stored["dup"]["same_site"] == "None"
    assert "age" in stored
    assert "case" in actual["requests"][1]["sent_cookies"]


def test_exact_header_byte_boundary_and_block_order(tmp_path):
    """Verify exact header byte boundaries and ordered header-limit blocks."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=25)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/x/y", "set_cookie": [
            "aa=1111; Path=/x; Secure",
            "bb=2222; Path=/x; Secure",
            "cc=3333; Path=/x; Secure",
            "dd=4444; Path=/x; Secure",
            "ee=5555; Path=/x; Secure",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/x/z", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["sent_cookies"] == ["aa", "bb", "cc"]
    assert actual["requests"][0]["cookie_header"] == "aa=1111; bb=2222; cc=3333"
    assert actual["requests"][0]["header_bytes"] == 25
    assert actual["requests"][0]["blocked_cookies"] == [
        {"name": "dd", "reason": "header_limit"},
        {"name": "ee", "reason": "header_limit"},
    ]
    assert actual["summary"]["truncated_requests"] == 1


def test_repeated_replacements_reorder_multiple_cookie_keys(tmp_path):
    """Verify repeated replacements reorder cookies while preserving distinct identities."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=200)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/a/b/c", "set_cookie": [
            "alpha=1; Path=/a; Secure",
            "beta=1; Path=/a; Secure",
            "gamma=1; Path=/a; Secure",
            "alpha=2; Path=/a; Secure; HttpOnly",
            "beta=2; Domain=.example.com; Path=/a; Secure",
            "beta=3; Path=/a; Secure",
            "delta=1; Path=/a/b; Secure",
            "delta=2; Path=/a/b; Secure",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/a/b/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q2", "url": "https://other.example.com/a/b/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["sent_cookies"] == ["gamma", "alpha", "beta", "beta", "delta"]
    assert actual["requests"][1]["sent_cookies"] == ["beta"]
    assert actual["requests"][0]["sent_cookie_keys"][2:4] == [
        {"name": "beta", "domain": "example.com", "path": "/a"},
        {"name": "beta", "domain": "app.example.com", "path": "/a"},
    ]
    assert {"name": "beta", "domain": "app.example.com", "path": "/a", "reason": "domain_mismatch"} in actual["requests"][1]["blocked_cookie_keys"]
    assert [c["name"] for c in actual["stored_cookies"]] == ["gamma", "alpha", "beta", "beta", "delta"]
    assert actual["stored_cookies"][2]["host_only"] is False
    assert actual["stored_cookies"][3]["host_only"] is True
    domains = {row["domain"]: row for row in actual["domain_diagnostics"]}
    assert domains["example.com"]["stored_cookie_count"] == 1
    assert domains["app.example.com"]["stored_cookie_count"] == 4
    assert domains["example.com"]["sent_count"] >= 1


def test_blocking_reason_precedence_and_repeated_request_stability(tmp_path):
    """Verify blocking reason precedence and that repeated requests do not mutate the jar."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=18)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/secure/set", "set_cookie": [
            "hostonly=1; Path=/secure; Secure; SameSite=Lax",
            "domainwide=1; Domain=.example.com; Path=/secure; Secure; SameSite=Lax",
            "pathmiss=1; Domain=.example.com; Path=/else; Secure; SameSite=Lax",
            "secureonly=1; Domain=.example.com; Path=/secure; Secure; SameSite=Lax",
            "strict=1; Domain=.example.com; Path=/secure; Secure; SameSite=Strict",
            "laxpost=1; Domain=.example.com; Path=/secure; Secure; SameSite=Lax",
            "fits=1; Domain=.example.com; Path=/secure; Secure; SameSite=None",
            "overflow=123456789; Domain=.example.com; Path=/secure; Secure; SameSite=None",
        ]},
        {"type": "request", "id": "q-http-cross-post", "url": "http://other.example.com/secure/page", "method": "POST", "top_level_site": "attacker.net", "is_top_level_navigation": False},
        {"type": "request", "id": "q-https-cross-post", "url": "https://other.example.com/secure/page", "method": "POST", "top_level_site": "attacker.net", "is_top_level_navigation": False},
        {"type": "request", "id": "q-https-cross-post-repeat", "url": "https://other.example.com/secure/page", "method": "POST", "top_level_site": "attacker.net", "is_top_level_navigation": False},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    first = actual["requests"][0]["blocked_cookies"]
    assert first[:6] == [
        {"name": "hostonly", "reason": "domain_mismatch"},
        {"name": "domainwide", "reason": "secure_only"},
        {"name": "pathmiss", "reason": "path_mismatch"},
        {"name": "secureonly", "reason": "secure_only"},
        {"name": "strict", "reason": "secure_only"},
        {"name": "laxpost", "reason": "secure_only"},
    ]
    second = actual["requests"][1]
    assert {"name": "strict", "reason": "samesite_strict"} in second["blocked_cookies"]
    assert {"name": "laxpost", "reason": "samesite_lax"} in second["blocked_cookies"]
    assert second == actual["requests"][2] | {"id": "q-https-cross-post"}
    assert actual["summary"]["truncated_requests"] >= 2


def test_case_sensitive_names_and_prefix_near_misses(tmp_path):
    """Verify cookie names are case-sensitive and prefix near-misses are ordinary names."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=200)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/login", "set_cookie": [
            "__secure-lower=1; Path=/; SameSite=None; Secure",
            "__host-lower=1; Domain=.example.com; Path=/; Secure",
            "__Secure-real=1; Path=/; Secure",
            "__Host-real=1; Path=/; Secure",
            "SID=upper; Path=/; Secure",
            "sid=lower; Path=/; Secure; HttpOnly",
            "AuthToken=mixed; Domain=.example.com; Path=/; Secure",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q2", "url": "https://other.example.com/", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    names = [c["name"] for c in actual["stored_cookies"]]
    assert "__secure-lower" in names
    assert "__host-lower" in names
    assert "SID" in names and "sid" in names
    risks = {c["name"]: c["risks"] for c in actual["stored_cookies"]}
    assert "missing_httponly" in risks["SID"]
    assert "missing_httponly" in risks["AuthToken"]
    assert actual["requests"][1]["sent_cookies"] == ["__host-lower", "AuthToken"]


def test_broader_generated_blocking_and_deletion_mix(tmp_path):
    """Verify a broad mixed log covers blocking, deletion, rejection, and truncation paths."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    policy.write_text(json.dumps({
        "public_suffixes": ["com", "net", "org", "co.uk", "uk", "internal"],
        "sensitive_name_patterns": ["session", "sid", "auth", "token", "secret"],
        "max_cookie_header_bytes": 58,
    }), encoding="utf-8")
    rows = []
    hosts = [
        "a.example.com",
        "b.example.com",
        "shop.service.co.uk",
        "cdn.service.co.uk",
        "edge.node.internal",
        "solo.testnet",
    ]
    for i in range(340):
        h = hosts[i % len(hosts)]
        if h.endswith("service.co.uk"):
            site = "service.co.uk"
            public_suffix = ".co.uk"
        elif h.endswith("internal"):
            site = "node.internal"
            public_suffix = ".internal"
        elif h.endswith("example.com"):
            site = "example.com"
            public_suffix = ".com"
        else:
            site = "testnet"
            public_suffix = ".net"
        path = f"/p/{i % 13}"
        rows.append({"type": "response", "id": f"r{i:03d}", "url": f"https://{h}{path}/set", "set_cookie": [
            f"session{i % 41}=s{i}; Domain=.{site}; Path=/; Secure; SameSite=Lax",
            f"local{i % 29}=l{i}; Path={path}; {'Secure' if i % 2 else ''}; SameSite={['Strict', 'Lax', 'None', 'Bad'][i % 4]}",
            f"secret{i % 17}=x{i}; Path=/p; HttpOnly" if i % 7 else f"ps{i}=bad; Domain={public_suffix}; Secure",
            f"old{i % 23}=gone; Path={path}; Max-Age={0 if i % 3 else -1}" if i % 11 else f"old{i % 23}=v{i}; Path={path}; Secure",
            f"old{i % 23}=clear; Path={path}; Max-Age=0" if i % 11 == 0 else f"noop{i}=clear; Path=/missing; Max-Age=0",
            f"dupe{i % 19}=a; Path=/bad; Path={path}; SameSite=Strict; SameSite=Lax; Secure",
        ]})
        rows.append({"type": "request", "id": f"q{i:03d}", "url": f"{'http' if i % 9 == 0 else 'https'}://{h}{path}/view", "method": "GET" if i % 4 else "POST", "top_level_site": site if i % 5 else "attacker.net", "is_top_level_navigation": i % 3 == 0})
        if i % 17 == 0:
            rows.append({"type": "request", "id": f"cross{i:03d}", "url": f"https://other.example.com{path}/view", "method": "POST", "top_level_site": "attacker.net", "is_top_level_navigation": False})
    write_jsonl(events, rows)
    actual = run_auditor(policy, events, timeout=60)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["summary"]["accepted"] > 900
    assert actual["summary"]["set_cookie_rejected"] > 45
    assert actual["summary"]["deleted"] > 5
    assert actual["summary"]["truncated_requests"] > 80


def test_adversarial_large_mixed_log_with_replacements(tmp_path):
    """Verify a large mixed log with replacements and truncation matches the reference."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    policy.write_text(json.dumps({
        "public_suffixes": ["com", "net", "org", "co.uk", "uk", "internal"],
        "sensitive_name_patterns": ["session", "sid", "auth", "token", "^sess"],
        "max_cookie_header_bytes": 74,
    }), encoding="utf-8")
    rows = []
    hosts = ["alpha.example.com", "beta.example.com", "login.service.co.uk", "api.service.co.uk", "node.internal"]
    for i in range(260):
        h = hosts[i % len(hosts)]
        if h.endswith("service.co.uk"):
            base = "service.co.uk"
            ps = ".co.uk"
        elif h.endswith("internal"):
            base = "node.internal"
            ps = ".internal"
        else:
            base = "example.com"
            ps = ".com"
        attrs = "Secure; HttpOnly" if i % 4 else "HttpOnly"
        same_site = ["Lax", "Strict", "None", "Invalid"][i % 4]
        rows.append({"type": "response", "id": f"r{i:03d}", "url": f"https://{h}/team/{i % 9}/login", "set_cookie": [
            f"sess{i % 37}=s{i}; Domain=.{base}; Path=/; {attrs}; SameSite=Lax",
            f"host{i % 23}=h{i}; Path=/team/{i % 9}; Secure; SameSite={same_site}",
            f"tok{i % 19}=t{i}; Path=/team; SameSite=None; Secure" if i % 6 else f"bad{i}=x; Domain={ps}; Secure",
            f"drop{i % 11}=gone; Path=/team/{i % 9}; Max-Age=0" if i % 10 else f"drop{i % 11}=v{i}; Path=/team/{i % 9}; Secure",
        ]})
        rows.append({"type": "request", "id": f"q{i:03d}", "url": f"https://{h}/team/{i % 9}/view", "method": "GET" if i % 3 else "POST", "top_level_site": base if i % 5 else "attacker.net", "is_top_level_navigation": i % 2 == 0})
        if i % 13 == 0:
            rows.append({"type": "request", "id": f"http{i:03d}", "url": f"http://{h}/team/{i % 9}/view", "method": "GET", "top_level_site": base, "is_top_level_navigation": True})
    write_jsonl(events, rows)
    actual = run_auditor(policy, events, timeout=40)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["summary"]["accepted"] > 500
    assert actual["summary"]["set_cookie_rejected"] > 40
    assert actual["summary"]["truncated_requests"] > 50


def test_zero_budget_blocks_all_eligible_and_tracks_truncation(tmp_path):
    """Verify zero header budget blocks every eligible cookie and records truncation."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=0)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/login", "set_cookie": [
            "a=1; Path=/; SameSite=Lax",
            "b=2; Path=/; SameSite=Lax",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/dashboard", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["sent_cookies"] == []
    assert actual["requests"][0]["sent_cookie_keys"] == []
    assert actual["requests"][0]["blocked_cookies"] == [
        {"name": "a", "reason": "header_limit"},
        {"name": "b", "reason": "header_limit"},
    ]
    assert all(entry["reason"] == "header_limit" for entry in actual["requests"][0]["blocked_cookies"])
    assert actual["requests"][0]["header_bytes"] == 0
    assert actual["summary"]["truncated_requests"] == 1


def test_continue_scanning_after_header_limit_truncation(tmp_path):
    """Verify scanning continues after an eligible cookie is blocked by the header limit."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=8)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/settings", "set_cookie": [
            "longname=toolong",
            "x=1; Path=/settings",
            "y=2; Path=/settings",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/settings/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["blocked_cookies"][0] == {"name": "longname", "reason": "header_limit"}
    assert actual["requests"][0]["sent_cookies"] == ["x", "y"]
    assert actual["requests"][0]["cookie_header"] == "x=1; y=2"
    assert actual["requests"][0]["header_bytes"] == len(actual["requests"][0]["cookie_header"])
    assert actual["requests"][0]["blocked_cookie_keys"][0]["name"] == "longname"


def test_header_limit_uses_utf8_byte_counts(tmp_path):
    """Verify header length accounting uses UTF-8 bytes for multibyte values."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=6)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/encode", "set_cookie": [
            "u=🧪; Path=/encode",
            "v=🍪; Path=/encode",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/encode/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["sent_cookies"] == ["u"]
    assert actual["requests"][0]["cookie_header"] == "u=🧪"
    assert actual["requests"][0]["header_bytes"] == len(actual["requests"][0]["cookie_header"].encode("utf-8"))
    assert actual["requests"][0]["blocked_cookies"] == [{"name": "v", "reason": "header_limit"}]


def test_method_case_normalization_and_domain_case_fold(tmp_path):
    """Verify request method, top-level site, and cookie domain case normalization."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=80)
    rows = [
        {"type": "response", "id": "r1", "url": "https://App.Example.Com/Section/Page", "set_cookie": [
            "a=1; Path=/section; SameSite=Lax",
            "b=2; Domain=.Example.Com; Path=/section; Secure; SameSite=None",
            "bad=3; Domain=.com",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com:443/section/item", "method": "get", "top_level_site": "EXAMPLE.COM", "is_top_level_navigation": False},
        {"type": "response", "id": "r2", "url": "https://app.example.com/section/other", "set_cookie": [
            "cross=4; Path=/section; SameSite=None",
        ]},
        {"type": "request", "id": "q2", "url": "https://app.example.com/section/item", "method": "POST", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["sent_cookies"] == ["a", "b"]
    assert [r["reason"] for r in actual["rejections"]] == [
        "public_suffix_domain",
        "samesite_none_without_secure",
    ]
    assert actual["requests"][1]["blocked_cookies"] == []


def test_domain_diagnostics_includes_blocked_only_domains(tmp_path):
    """Verify diagnostics retain domains that only appear in blocked cookie events."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=80)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/edge", "set_cookie": [
            "alpha=1; Domain=.example.com; Path=/; Secure",
        ]},
        {"type": "request", "id": "q1", "url": "https://other.example.net/edge", "method": "GET", "top_level_site": "other.example.net", "is_top_level_navigation": True},
        {"type": "response", "id": "r2", "url": "https://app.example.com/edge", "set_cookie": [
            "alpha=2; Domain=.example.com; Path=/; Max-Age=0; Secure",
        ]},
        {"type": "request", "id": "q2", "url": "https://app.example.com/edge", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    diag = {row["domain"]: row for row in actual["domain_diagnostics"]}
    assert "example.com" in diag
    assert diag["example.com"]["stored_cookie_count"] == 0
    assert diag["example.com"]["blocked_count"] == 1
    assert diag["example.com"]["sent_count"] == 0


def test_repeated_requests_do_not_mutate_jar_state(tmp_path):
    """Verify identical repeated requests produce identical output without jar mutation."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=200)
    rows = [
        {"type": "response", "id": "r1", "url": "https://shop.example.com/path", "set_cookie": [
            "sid=live; Path=/path; Secure; HttpOnly; SameSite=Lax",
        ]},
        {"type": "request", "id": "q1", "url": "https://shop.example.com/path/item", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q2", "url": "https://shop.example.com/path/item", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    first = {k: v for k, v in actual["requests"][0].items() if k != "id"}
    second = {k: v for k, v in actual["requests"][1].items() if k != "id"}
    assert_equal(first, second)
    # Both requests must emit identical wire output; request handling must remain pure/read-only with respect to the jar.
    assert_equal(actual["requests"][0]["cookie_header"], actual["requests"][1]["cookie_header"])


def test_port_in_url_does_not_affect_cookie_matching(tmp_path):
    """Verify URL ports are ignored for host and domain cookie matching."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=120)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com:8443/auth/login", "set_cookie": [
            "session=ok; Path=/auth; SameSite=Lax",
            "wide=ok; Domain=.Example.Com; Path=/; Secure; SameSite=Lax",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com:9443/auth/echo", "method": "get", "top_level_site": "EXAMPLE.COM", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["sent_cookies"] == ["session", "wide"]


def test_request_level_truncation_reapplies_for_each_request(tmp_path):
    """Verify header truncation is evaluated independently for each request."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    policy.write_text(json.dumps({
            "public_suffixes": ["com"],
            "sensitive_name_patterns": ["session", "sid", "auth", "token"],
            "max_cookie_header_bytes": 0,
        }), encoding="utf-8")
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/a", "set_cookie": [
            "u=longvalue; Path=/a",
            "v=2; Path=/a",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/a", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q2", "url": "https://app.example.com/a", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q3", "url": "https://app.example.com/a", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["summary"]["truncated_requests"] == 3
    blocked_per_request = [len(r["blocked_cookies"]) for r in actual["requests"]]
    assert blocked_per_request == [2, 2, 2]
    assert actual["requests"][0]["blocked_cookies"] == [{"name": "u", "reason": "header_limit"}, {"name": "v", "reason": "header_limit"}]
    assert actual["requests"][0]["cookie_header"] == ""


def test_longest_public_suffix_and_cross_subdomain_state_pressure(tmp_path):
    """Verify longest public suffix handling across subdomains under SameSite pressure."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    policy.write_text(json.dumps({
        "public_suffixes": ["uk", "co.uk", "example.co.uk", "internal"],
        "sensitive_name_patterns": ["sid", "session", "auth", "token"],
        "max_cookie_header_bytes": 140,
    }), encoding="utf-8")
    rows = [
        {"type": "response", "id": "r1", "url": "https://shop.customer.example.co.uk/a/b/login", "set_cookie": [
            "wide=1; Domain=.customer.example.co.uk; Path=/; Secure; SameSite=Strict",
            "host=1; Path=/a/b; Secure; SameSite=Lax",
            "ps=bad; Domain=.example.co.uk; Secure",
            "badsub=bad; Domain=.other.example.co.uk; Secure",
        ]},
        {"type": "request", "id": "same-site-sub", "url": "https://api.customer.example.co.uk/a/b/page", "method": "POST", "top_level_site": "customer.example.co.uk", "is_top_level_navigation": False},
        {"type": "request", "id": "cross-site-nav", "url": "https://shop.customer.example.co.uk/a/b/page", "method": "GET", "top_level_site": "other.example.co.uk", "is_top_level_navigation": True},
        {"type": "request", "id": "cross-site-post", "url": "https://shop.customer.example.co.uk/a/b/page", "method": "POST", "top_level_site": "other.example.co.uk", "is_top_level_navigation": False},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert [r["reason"] for r in actual["rejections"]] == ["public_suffix_domain", "domain_not_suffix"]
    assert "wide" in actual["requests"][0]["sent_cookies"]
    assert {"name": "wide", "reason": "samesite_strict"} in actual["requests"][1]["blocked_cookies"]
    assert {"name": "host", "reason": "samesite_lax"} in actual["requests"][2]["blocked_cookies"]


def test_interleaved_replacement_deletion_and_report_order_pressure(tmp_path):
    """Verify interleaved replacements and deletions preserve report order and keys."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=60)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/cart/view", "set_cookie": [
            "cart=one; Path=/cart; Secure; HttpOnly",
            "promo=aa; Path=/cart; Secure",
            "cart=two; Path=/cart; Secure; HttpOnly",
            "sid=s1; Path=/; Secure; HttpOnly",
            "promo=drop; Path=/cart; Max-Age=0",
            "cart=three; Path=/cart; Secure; HttpOnly",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/cart/checkout", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "response", "id": "r2", "url": "https://app.example.com/cart/edit", "set_cookie": [
            "cart=gone; Path=/wrong; Max-Age=0",
            "sid=gone; Path=/; Max-Age=0",
            "promo=bb; Path=/cart; Secure",
        ]},
        {"type": "request", "id": "q2", "url": "https://app.example.com/cart/checkout", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["responses"][0]["accepted_cookie_keys"] == [
        {"name": "cart", "domain": "app.example.com", "path": "/cart"},
        {"name": "promo", "domain": "app.example.com", "path": "/cart"},
        {"name": "cart", "domain": "app.example.com", "path": "/cart"},
        {"name": "sid", "domain": "app.example.com", "path": "/"},
        {"name": "cart", "domain": "app.example.com", "path": "/cart"},
    ]
    assert actual["responses"][0]["deleted_cookie_keys"] == [{"name": "promo", "domain": "app.example.com", "path": "/cart"}]
    assert actual["responses"][1]["deleted_cookie_keys"] == [{"name": "sid", "domain": "app.example.com", "path": "/"}]
    assert actual["requests"][0]["sent_cookies"] == ["sid", "cart"]
    assert actual["requests"][1]["sent_cookies"] == ["cart", "promo"]


def test_multibyte_header_skip_then_fit_later_cookie(tmp_path):
    """Verify a multibyte overflow cookie does not prevent later fitting cookies from sending."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=14)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/emoji/start", "set_cookie": [
            "a=1; Path=/emoji",
            "wide=🧪🧪; Path=/emoji",
            "b=2; Path=/emoji",
            "c=🍪; Path=/emoji",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/emoji/view", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["sent_cookies"] == ["a", "b"]
    assert actual["requests"][0]["cookie_header"] == "a=1; b=2"
    assert actual["requests"][0]["header_bytes"] == len("a=1; b=2".encode("utf-8"))
    assert actual["requests"][0]["blocked_cookies"] == [
        {"name": "wide", "reason": "header_limit"},
        {"name": "c", "reason": "header_limit"},
    ]


def test_large_replacement_churn_keeps_cookie_identity_and_diagnostics_exact(tmp_path):
    """Verify large replacement churn keeps identities and diagnostics exact."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=72)
    rows = []
    for i in range(90):
        host = "app.example.com" if i % 2 == 0 else "api.example.com"
        rows.append({"type": "response", "id": f"r{i:03d}", "url": f"https://{host}/tenant/{i % 7}/page", "set_cookie": [
            f"sid{i % 9}=v{i}; Domain=.example.com; Path=/; Secure; HttpOnly; SameSite=Lax",
            f"local{i % 5}=h{i}; Path=/tenant/{i % 7}; SameSite=Strict",
            f"auth{i % 4}=a{i}; Path=/tenant; SameSite=None; Secure",
            f"local{i % 5}=gone; Path=/tenant/{i % 7}; Max-Age=0" if i % 6 == 0 else f"pref{i % 11}=p{i}; Path=/tenant; Secure",
        ]})
        rows.append({"type": "request", "id": f"q{i:03d}", "url": f"https://{host}/tenant/{i % 7}/next", "method": "GET" if i % 4 else "POST", "top_level_site": "example.com" if i % 5 else "other.net", "is_top_level_navigation": i % 3 == 0})
    write_jsonl(events, rows)
    actual = run_auditor(policy, events, timeout=20)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["summary"]["accepted"] > 250
    assert actual["summary"]["deleted"] > 5
    assert actual["summary"]["truncated_requests"] > 20
    assert any(row["domain"] == "example.com" and row["sent_count"] > 0 and row["blocked_count"] > 0 for row in actual["domain_diagnostics"])


def test_duplicate_attribute_last_value_controls_domain_path_samesite_and_max_age(tmp_path):
    """Verify later duplicate attributes control domain, path, SameSite, and Max-Age behavior."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=200)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/one/two/page", "set_cookie": [
            "flip=1; Domain=.com; Domain=.example.com; Path=/bad; Path=/one; SameSite=None; SameSite=Lax",
            "temp=1; Path=/one; Max-Age=0; Max-Age=not-a-delete",
            "gone=live; Path=/one; Secure",
            "gone=dead; Path=/one; Max-Age=still-not; Max-Age=0",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/one/two/page", "method": "POST", "top_level_site": "other.net", "is_top_level_navigation": False},
        {"type": "request", "id": "q2", "url": "https://api.example.com/one/two/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["rejections"] == []
    assert actual["summary"]["deleted"] == 1
    assert actual["responses"][0]["accepted_cookie_keys"] == [
        {"name": "flip", "domain": "example.com", "path": "/one"},
        {"name": "temp", "domain": "app.example.com", "path": "/one"},
        {"name": "gone", "domain": "app.example.com", "path": "/one"},
    ]
    assert actual["responses"][0]["deleted_cookie_keys"] == [{"name": "gone", "domain": "app.example.com", "path": "/one"}]
    audit = actual["set_cookie_audit"]
    assert audit[0]["domain"] == "example.com"
    assert audit[0]["path"] == "/one"
    assert audit[0]["same_site"] == "Lax"
    assert audit[0]["disposition"] == "accepted"
    assert audit[1]["name"] == "temp"
    assert audit[1]["max_age_state"] == "invalid"
    assert audit[1]["disposition"] == "accepted"
    assert audit[3]["name"] == "gone"
    assert audit[3]["max_age_state"] == "delete"
    assert audit[3]["disposition"] == "deleted"
    assert {"name": "flip", "reason": "samesite_lax"} in actual["requests"][0]["blocked_cookies"]
    assert actual["requests"][1]["sent_cookies"] == ["flip"]


def test_header_limit_exact_separator_boundary_after_prior_block(tmp_path):
    """Verify separator byte accounting after a prior header-limit block."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=8)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/hdr/start", "set_cookie": [
            "too=123456; Path=/hdr",
            "a=1; Path=/hdr",
            "b=2; Path=/hdr",
            "c=3; Path=/hdr",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/hdr/next", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["sent_cookies"] == ["a", "b"]
    assert actual["requests"][0]["cookie_header"] == "a=1; b=2"
    assert actual["requests"][0]["header_bytes"] == 8
    assert actual["requests"][0]["blocked_cookies"] == [
        {"name": "too", "reason": "header_limit"},
        {"name": "c", "reason": "header_limit"},
    ]
    assert actual["summary"]["truncated_requests"] == 1


def test_risk_counts_clear_after_deletion_but_diagnostics_keep_sent_and_blocked_domains(tmp_path):
    """Verify deleting risky cookies clears risk counts while preserving diagnostics history."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=40)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/secure/login", "set_cookie": [
            "authLoose=secret; Domain=.example.com; Path=/secure",
            "sidLocal=secret; Path=/secure; HttpOnly",
        ]},
        {"type": "request", "id": "q1", "url": "http://other.example.com/secure/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "response", "id": "r2", "url": "https://app.example.com/secure/logout", "set_cookie": [
            "authLoose=gone; Domain=.example.com; Path=/secure; Max-Age=0",
            "sidLocal=gone; Path=/secure; Max-Age=0",
        ]},
        {"type": "request", "id": "q2", "url": "https://app.example.com/secure/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["summary"]["risk_counts"] == {}
    assert actual["summary"]["deleted"] == 2
    diag = {row["domain"]: row for row in actual["domain_diagnostics"]}
    assert diag["example.com"]["stored_cookie_count"] == 0
    assert diag["example.com"]["sent_count"] == 1
    assert diag["example.com"]["risk_counts"] == {}
    assert diag["app.example.com"]["stored_cookie_count"] == 0
    assert diag["app.example.com"]["blocked_count"] == 1
    assert actual["stored_cookies"] == []


def test_empty_response_and_request_only_logs_keep_schema_arrays_and_counts(tmp_path):
    """Verify request-only and empty-response logs keep array schemas and summary counts."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=80)
    rows = [
        {"type": "request", "id": "q0", "url": "https://app.example.com/start", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "response", "id": "r-empty", "url": "https://app.example.com/start", "set_cookie": []},
        {"type": "request", "id": "q1", "url": "https://app.example.com/start", "method": "POST", "top_level_site": "other.net", "is_top_level_navigation": False},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["summary"] == {
        "accepted": 0,
        "set_cookie_rejected": 0,
        "deleted": 0,
        "request_count": 2,
        "risk_counts": {},
        "truncated_requests": 0,
    }
    assert actual["responses"] == [{"id": "r-empty", "accepted_cookie_keys": [], "deleted_cookie_keys": []}]
    assert actual["requests"][0]["sent_cookies"] == []
    assert actual["requests"][1]["blocked_cookie_keys"] == []
    assert actual["rejections"] == []
    assert actual["domain_diagnostics"] == []
    assert actual["stored_cookies"] == []


def test_cookie_values_with_equals_blank_attributes_and_empty_value_names(tmp_path):
    """Verify values with equals signs, blank attributes, empty values, and empty names."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=160)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/path/login", "set_cookie": [
            "encoded=a=b=c; ; Path=/path; Secure; HttpOnly",
            "emptyvalue=; Path=/path; SameSite=Bad",
            " spaced =  has spaces  ; Path=/path; Secure",
            "=nameless; Path=/path; Secure",
        ]},
        {"type": "request", "id": "q1", "url": "https://app.example.com/path/next", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["rejections"] == [{"event_id": "r1", "name": "", "reason": "empty_name"}]
    assert actual["requests"][0]["sent_cookies"] == ["encoded", "emptyvalue", "spaced"]
    assert actual["requests"][0]["cookie_header"] == "encoded=a=b=c; emptyvalue=; spaced=has spaces"
    stored = {c["name"]: c for c in actual["stored_cookies"]}
    assert stored["encoded"]["secure"] is True
    assert stored["emptyvalue"]["same_site"] == "Lax"
    assert "spaced" in stored


def test_path_boundary_matrix_and_url_empty_path_default(tmp_path):
    """Verify path boundary matching and default path behavior for URLs without paths."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=200)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com", "set_cookie": [
            "root=1",
            "slash=1; Path=/",
            "app=1; Path=/app",
            "apps=1; Path=/apps",
            "deep=1; Path=/app/deep",
        ]},
        {"type": "request", "id": "q-root", "url": "https://app.example.com/", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q-app", "url": "https://app.example.com/app", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q-app-page", "url": "https://app.example.com/app/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q-apps", "url": "https://app.example.com/apps/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["responses"][0]["accepted_cookie_keys"][0] == {"name": "root", "domain": "app.example.com", "path": "/"}
    assert actual["requests"][0]["sent_cookies"] == ["root", "slash"]
    assert actual["requests"][1]["sent_cookies"] == ["root", "slash", "app"]
    assert actual["requests"][2]["sent_cookies"] == ["root", "slash", "app"]
    assert actual["requests"][3]["sent_cookies"] == ["root", "slash", "apps"]


def test_same_name_host_only_and_domain_cookies_remain_distinct_until_exact_delete(tmp_path):
    """Verify same-name host-only and domain cookies stay distinct until exact deletion."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=200)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/login", "set_cookie": [
            "sid=host; Path=/; Secure; HttpOnly",
            "sid=domain; Domain=.example.com; Path=/; Secure; HttpOnly",
            "theme=host; Path=/; Secure",
            "theme=domain; Domain=.example.com; Path=/; Secure",
        ]},
        {"type": "request", "id": "q-before", "url": "https://app.example.com/home", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "response", "id": "r2", "url": "https://app.example.com/logout", "set_cookie": [
            "sid=gone; Domain=.example.com; Path=/; Max-Age=0",
            "theme=gone; Path=/; Max-Age=0",
        ]},
        {"type": "request", "id": "q-app-after", "url": "https://app.example.com/home", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q-api-after", "url": "https://api.example.com/home", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["sent_cookies"] == ["sid", "sid", "theme", "theme"]
    assert actual["requests"][0]["sent_cookie_keys"] == [
        {"name": "sid", "domain": "app.example.com", "path": "/"},
        {"name": "sid", "domain": "example.com", "path": "/"},
        {"name": "theme", "domain": "app.example.com", "path": "/"},
        {"name": "theme", "domain": "example.com", "path": "/"},
    ]
    assert actual["responses"][1]["deleted_cookie_keys"] == [
        {"name": "sid", "domain": "example.com", "path": "/"},
        {"name": "theme", "domain": "app.example.com", "path": "/"},
    ]
    assert actual["requests"][1]["sent_cookies"] == ["sid", "theme"]
    assert actual["requests"][2]["sent_cookies"] == ["theme"]
    stored_keys = {(c["name"], c["domain"], c["path"]) for c in actual["stored_cookies"]}
    assert stored_keys == {("sid", "app.example.com", "/"), ("theme", "example.com", "/")}


def test_exact_cookie_identity_replacement_does_not_merge_same_name_different_paths(tmp_path):
    """Verify replacement and deletion use exact cookie identity across different paths."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=180)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/app/login", "set_cookie": [
            "mode=root; Path=/; Secure",
            "mode=app; Path=/app; Secure",
            "mode=deep; Path=/app/deep; Secure",
            "mode=app2; Path=/app; Secure",
        ]},
        {"type": "request", "id": "q-deep", "url": "https://app.example.com/app/deep/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "response", "id": "r2", "url": "https://app.example.com/app/logout", "set_cookie": [
            "mode=gone; Path=/app; Max-Age=0",
        ]},
        {"type": "request", "id": "q-after", "url": "https://app.example.com/app/deep/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["sent_cookies"] == ["mode", "mode", "mode"]
    assert actual["requests"][0]["sent_cookie_keys"] == [
        {"name": "mode", "domain": "app.example.com", "path": "/"},
        {"name": "mode", "domain": "app.example.com", "path": "/app/deep"},
        {"name": "mode", "domain": "app.example.com", "path": "/app"},
    ]
    assert actual["responses"][1]["deleted_cookie_keys"] == [{"name": "mode", "domain": "app.example.com", "path": "/app"}]
    assert actual["requests"][1]["sent_cookie_keys"] == [
        {"name": "mode", "domain": "app.example.com", "path": "/"},
        {"name": "mode", "domain": "app.example.com", "path": "/app/deep"},
    ]


def test_duplicate_final_attributes_and_rejection_priority_composite(tmp_path):
    """Verify later duplicate attributes control validation, deletion, and audit normalization."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    policy.write_text(json.dumps({
        "public_suffixes": ["com", "net", "co.uk"],
        "sensitive_name_patterns": ["session", "sid", "auth", "token", "secret"],
        "max_cookie_header_bytes": 120,
    }), encoding="utf-8")
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/a/b/start", "set_cookie": [
            "flip=old; Path=/a; Max-Age=0; Max-Age=5; Secure",
            "flip=gone; Path=/a; Max-Age=5; Max-Age=0",
            "dom=wide; Domain=.com; Domain=..Example.COM; Path=/a; Secure",
            "dom=delete; Domain=example.com; Path=/a; Max-Age=0; Domain=.com",
            "ss=ok; Path=/a; SameSite=None; SameSite=Lax",
            "ssbad=no; Path=/a; SameSite=Lax; SameSite=None",
            "__Secure-dupe=ok; Path=/a; Secure; SameSite=Strict",
            "__Host-late=bad; Domain=.example.com; Path=/bad; Path=/; Secure",
            "emptylater=1; Domain=..example.com; Domain=.; Path=/a",
        ]},
        {"type": "request", "id": "q-cross-post", "url": "https://app.example.com/a/page", "method": "POST", "top_level_site": "attacker.net", "is_top_level_navigation": False},
        {"type": "request", "id": "q-same", "url": "https://app.example.com/a/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["responses"][0]["accepted_cookie_keys"] == [
        {"name": "flip", "domain": "app.example.com", "path": "/a"},
        {"name": "dom", "domain": "example.com", "path": "/a"},
        {"name": "ss", "domain": "app.example.com", "path": "/a"},
        {"name": "__Secure-dupe", "domain": "app.example.com", "path": "/a"},
    ]
    assert actual["responses"][0]["deleted_cookie_keys"] == [
        {"name": "flip", "domain": "app.example.com", "path": "/a"},
    ]
    assert [r["reason"] for r in actual["rejections"]] == [
        "public_suffix_domain",
        "samesite_none_without_secure",
        "host_prefix_invalid",
        "domain_not_suffix",
    ]
    audit = {(row["name"], row["index"]): row for row in actual["set_cookie_audit"]}
    assert audit[("flip", 0)]["max_age_state"] == "positive"
    assert audit[("flip", 1)]["disposition"] == "deleted"
    assert audit[("dom", 2)]["domain"] == "example.com"
    assert audit[("ss", 4)]["same_site"] == "Lax"
    assert audit[("ssbad", 5)]["reason"] == "samesite_none_without_secure"
    assert {"name": "__Secure-dupe", "reason": "samesite_strict"} in actual["requests"][0]["blocked_cookies"]
    assert actual["requests"][1]["sent_cookies"] == ["dom", "ss", "__Secure-dupe"]


def test_lifecycle_reaccept_after_delete_and_later_header_limit_block(tmp_path):
    """Verify lifecycle rows merge reaccept-after-delete observations for the same identity."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=3)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/", "set_cookie": [
            "a=1; Path=/",
        ]},
        {"type": "request", "id": "q-sent", "url": "https://app.example.com/", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "response", "id": "r2", "url": "https://app.example.com/logout", "set_cookie": [
            "a=gone; Path=/; Max-Age=0",
        ]},
        {"type": "response", "id": "r3", "url": "https://app.example.com/login", "set_cookie": [
            "a=long; Path=/",
        ]},
        {"type": "request", "id": "q-blocked", "url": "https://app.example.com/", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["requests"][0]["cookie_header"] == "a=1"
    assert actual["requests"][1]["cookie_header"] == ""
    assert actual["requests"][1]["blocked_cookie_keys"] == [
        {"name": "a", "domain": "app.example.com", "path": "/", "reason": "header_limit"},
    ]
    assert actual["summary"]["accepted"] == 2
    assert actual["summary"]["deleted"] == 1
    assert actual["summary"]["truncated_requests"] == 1
    lifecycle = actual["cookie_lifecycle"][0]
    assert lifecycle == {
        "name": "a",
        "domain": "app.example.com",
        "path": "/",
        "accepted_count": 2,
        "replaced_count": 0,
        "deleted_count": 1,
        "sent_count": 1,
        "blocked_count": 1,
        "first_event_id": "r1",
        "last_event_id": "q-blocked",
        "final_state": "stored",
    }


def test_generated_multisite_churn_with_duplicate_attributes_and_lifecycle_pressure(tmp_path):
    """Verify a high-churn multisite log with duplicate attributes, deletes, and diagnostics."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    policy.write_text(json.dumps({
        "public_suffixes": ["com", "net", "org", "co.uk", "uk", "internal"],
        "sensitive_name_patterns": ["session", "sid", "auth", "token", "secret", "^s"],
        "max_cookie_header_bytes": 67,
    }), encoding="utf-8")
    rows = []
    hosts = [
        "app.example.com",
        "cdn.example.com",
        "shop.service.co.uk",
        "api.service.co.uk",
        "node.mesh.internal",
        "edge.mesh.internal",
    ]
    for i in range(520):
        h = hosts[i % len(hosts)]
        if h.endswith("service.co.uk"):
            site = "service.co.uk"
            public_domain = ".co.uk"
        elif h.endswith("mesh.internal"):
            site = "mesh.internal"
            public_domain = ".internal"
        else:
            site = "example.com"
            public_domain = ".com"
        path = f"/zone/{i % 11}"
        rows.append({"type": "response", "id": f"r{i:04d}", "url": f"https://{h}{path}/set", "set_cookie": [
            f"session{i % 53}=s{i}; Domain=.{site}; Domain=..{site.upper()}; Path=/; Secure; HttpOnly; SameSite=Strict; SameSite=Lax",
            f"local{i % 47}=l{i}; Path=/wrong; Path={path}; SameSite=None; SameSite={'None' if i % 4 == 0 else 'Lax'}; {'Secure' if i % 4 == 0 else ''}",
            f"secret{i % 31}=x{i}; Path=/zone; Max-Age=bad; HttpOnly" if i % 6 else f"badps{i}=x; Domain={public_domain}; SameSite=None",
            f"recur{i % 29}=v{i}; Domain=.{site}; Path={path}; Secure" if i % 9 == 0 else (
                f"recur{(i - 1) % 29}=gone; Domain=.{site}; Path=/zone/{(i - 1) % 11}; Max-Age=0"
                if i % 9 == 1 else f"recur{i % 29}=gone; Domain=.{site}; Path={path}; Max-Age=0"
            ),
            f"dupe{i % 37}=a; Path=/old; Path={path}; Domain=.not-{site}; Domain=.{site}; SameSite=Bad; SameSite=Lax",
        ]})
        rows.append({"type": "request", "id": f"q{i:04d}", "url": f"{'http' if i % 10 == 0 else 'https'}://{h}{path}/view", "method": "GET" if i % 5 else "POST", "top_level_site": site if i % 7 else "attacker.net", "is_top_level_navigation": i % 3 == 0})
        if i % 19 == 0:
            rows.append({"type": "request", "id": f"cross{i:04d}", "url": f"https://other.example.com{path}/view", "method": "POST", "top_level_site": "attacker.net", "is_top_level_navigation": False})
    write_jsonl(events, rows)
    actual = run_auditor(policy, events, timeout=90)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["summary"]["accepted"] > 1600
    assert actual["summary"]["set_cookie_rejected"] > 80
    assert actual["summary"]["deleted"] > 15
    assert actual["summary"]["truncated_requests"] > 200
    assert len(actual["cookie_lifecycle"]) > 500
    assert len(actual["domain_diagnostics"]) >= 6


def test_nested_public_suffix_site_and_domain_rejection_pressure(tmp_path):
    """Verify longest nested public suffixes affect Domain rejection and SameSite context."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    policy.write_text(json.dumps({
        "public_suffixes": ["com", "github.io", "pages.github.io"],
        "sensitive_name_patterns": ["sid", "token"],
        "max_cookie_header_bytes": 140,
    }), encoding="utf-8")
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.team.pages.github.io/a/b/set", "set_cookie": [
            "wide=bad; Domain=.pages.github.io; Path=/; Secure",
            "team=ok; Domain=.team.pages.github.io; Path=/; Secure; SameSite=Strict",
            "host=ok; Path=/a; Secure; SameSite=Lax",
            "api=bad; Domain=.api.team.pages.github.io; Path=/; Secure",
            "token=loose; Domain=.team.pages.github.io; Path=/; Secure",
        ]},
        {"type": "request", "id": "same-site-api", "url": "https://api.team.pages.github.io/a/view", "method": "POST", "top_level_site": "team.pages.github.io", "is_top_level_navigation": False},
        {"type": "request", "id": "cross-site-api", "url": "https://api.team.pages.github.io/a/view", "method": "GET", "top_level_site": "other.pages.github.io", "is_top_level_navigation": True},
        {"type": "request", "id": "same-host-cross", "url": "https://app.team.pages.github.io/a/view", "method": "POST", "top_level_site": "other.pages.github.io", "is_top_level_navigation": False},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert [r["reason"] for r in actual["rejections"]] == ["public_suffix_domain", "domain_not_suffix"]
    same_diag = next(row for row in actual["request_diagnostics"] if row["id"] == "same-site-api")
    assert same_diag["registrable_site"] == "team.pages.github.io"
    assert same_diag["same_site_context"] is True
    assert actual["requests"][0]["sent_cookies"] == ["team", "token"]
    assert {"name": "team", "reason": "samesite_strict"} in actual["requests"][1]["blocked_cookies"]
    assert {"name": "host", "reason": "samesite_lax"} in actual["requests"][2]["blocked_cookies"]


def test_same_identity_churn_across_host_domain_and_paths_under_tiny_budget(tmp_path):
    """Verify exact identity churn while same-name cookies coexist across scopes and paths."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    write_policy(policy, max_bytes=16)
    rows = [
        {"type": "response", "id": "r1", "url": "https://app.example.com/app/login", "set_cookie": [
            "sid=h1; Path=/; Secure; HttpOnly",
            "sid=d1; Domain=.example.com; Path=/; Secure; HttpOnly",
            "sid=happ1; Path=/app; Secure",
            "sid=dapp1; Domain=.example.com; Path=/app; Secure",
            "sid=happ2; Path=/app; Secure; HttpOnly",
            "sid=dapp2; Domain=.example.com; Path=/app; Secure; HttpOnly",
            "sid=gone; Path=/; Max-Age=0",
            "sid=h2; Path=/; Secure; HttpOnly",
        ]},
        {"type": "request", "id": "q-app", "url": "https://app.example.com/app/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "request", "id": "q-api", "url": "https://api.example.com/app/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
        {"type": "response", "id": "r2", "url": "https://app.example.com/app/logout", "set_cookie": [
            "sid=gone; Domain=.example.com; Path=/app; Max-Age=0",
            "sid=gone; Path=/app; Max-Age=0",
        ]},
        {"type": "request", "id": "q-after", "url": "https://app.example.com/app/page", "method": "GET", "top_level_site": "example.com", "is_top_level_navigation": True},
    ]
    write_jsonl(events, rows)
    actual = run_auditor(policy, events)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["summary"]["accepted"] == 7
    assert actual["summary"]["deleted"] == 3
    assert actual["summary"]["truncated_requests"] >= 2
    assert actual["requests"][0]["sent_cookies"] == ["sid", "sid"]
    assert actual["requests"][0]["blocked_cookies"] == [
        {"name": "sid", "reason": "header_limit"},
        {"name": "sid", "reason": "header_limit"},
    ]
    assert actual["requests"][1]["sent_cookies"] == ["sid"]
    assert {"name": "sid", "domain": "app.example.com", "path": "/", "reason": "domain_mismatch"} in actual["requests"][1]["blocked_cookie_keys"]
    assert actual["requests"][2]["sent_cookie_keys"] == [
        {"name": "sid", "domain": "example.com", "path": "/"},
        {"name": "sid", "domain": "app.example.com", "path": "/"},
    ]
    lifecycle = {(row["name"], row["domain"], row["path"]): row for row in actual["cookie_lifecycle"]}
    assert lifecycle[("sid", "app.example.com", "/app")]["replaced_count"] == 1
    assert lifecycle[("sid", "example.com", "/app")]["deleted_count"] == 1
    assert lifecycle[("sid", "app.example.com", "/app")]["final_state"] == "absent"


def test_large_reaccept_delete_header_limit_and_domain_history_pressure(tmp_path):
    """Verify large repeated accept/delete/reaccept cycles preserve diagnostics and lifecycle counts."""
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    policy.write_text(json.dumps({
        "public_suffixes": ["com", "net", "co.uk", "internal"],
        "sensitive_name_patterns": ["session", "sid", "auth", "token", "secret"],
        "max_cookie_header_bytes": 41,
    }), encoding="utf-8")
    rows = []
    hosts = ["a.example.com", "b.example.com", "shop.service.co.uk", "node.mesh.internal"]
    for i in range(360):
        h = hosts[i % len(hosts)]
        if h.endswith("service.co.uk"):
            site = "service.co.uk"
        elif h.endswith("mesh.internal"):
            site = "mesh.internal"
        else:
            site = "example.com"
        path = f"/p/{i % 9}"
        rows.append({"type": "response", "id": f"r{i:04d}", "url": f"https://{h}{path}/set", "set_cookie": [
            f"sid{i % 23}=h{i}; Path={path}; Secure; HttpOnly; SameSite=Lax",
            f"sid{i % 23}=d{i}; Domain=.{site}; Path={path}; Secure; HttpOnly; SameSite=Lax",
            f"temp{i % 17}=v{i}; Domain=.{site}; Path=/p; Secure" if i % 4 == 0 else f"temp{i % 17}=gone; Domain=.{site}; Path=/p; Max-Age=0",
            f"auth{i % 19}=loose{i}; Path=/; SameSite=None; Secure" if i % 5 else f"bad{i}=x; Domain=.com",
        ]})
        rows.append({"type": "request", "id": f"q{i:04d}", "url": f"{'http' if i % 13 == 0 else 'https'}://{h}{path}/view", "method": "GET" if i % 6 else "POST", "top_level_site": site if i % 8 else "attacker.net", "is_top_level_navigation": i % 2 == 0})
        if i % 15 == 0:
            rows.append({"type": "response", "id": f"clear{i:04d}", "url": f"https://{h}{path}/clear", "set_cookie": [
                f"sid{i % 23}=gone; Path={path}; Max-Age=0",
                f"sid{i % 23}=gone; Domain=.{site}; Path={path}; Max-Age=0",
            ]})
    write_jsonl(events, rows)
    actual = run_auditor(policy, events, timeout=90)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["summary"]["accepted"] > 900
    assert actual["summary"]["deleted"] > 30
    assert actual["summary"]["truncated_requests"] > 120
    assert len(actual["cookie_lifecycle"]) > 250
    deleted_rows = [row for row in actual["cookie_lifecycle"] if row["deleted_count"] > 0]
    assert len(deleted_rows) > 25


def test_seeded_random_scope_churn_fuzz_against_reference(tmp_path):
    """Verify a deterministic randomized mix of scope, replacement, deletion, and request rules."""
    rng = random.Random(732451)
    policy = tmp_path / "policy.json"
    events = tmp_path / "events.jsonl"
    policy.write_text(json.dumps({
        "public_suffixes": ["com", "net", "org", "co.uk", "uk", "internal", "github.io", "pages.github.io"],
        "sensitive_name_patterns": ["session", "sid", "auth", "token", "secret", "^s"],
        "max_cookie_header_bytes": 53,
    }), encoding="utf-8")
    hosts = [
        ("app.example.com", "example.com", ".com"),
        ("cdn.example.com", "example.com", ".com"),
        ("shop.service.co.uk", "service.co.uk", ".co.uk"),
        ("api.service.co.uk", "service.co.uk", ".co.uk"),
        ("node.mesh.internal", "mesh.internal", ".internal"),
        ("app.team.pages.github.io", "team.pages.github.io", ".pages.github.io"),
    ]
    rows = []
    for i in range(420):
        host_name, site, public_domain = hosts[rng.randrange(len(hosts))]
        path = f"/bucket/{rng.randrange(8)}/p{rng.randrange(5)}"
        slot = i % 31
        headers = [
            f"session{slot}=s{i}; Domain=.{site}; Path=/; Secure; HttpOnly; SameSite=Strict; SameSite=Lax",
            f"local{slot}=l{i}; Path={path}; {'Secure' if rng.randrange(3) else ''}; SameSite={rng.choice(['Lax', 'Strict', 'Bad'])}",
            f"cycle{slot}=v{i}; Domain=.{site}; Path=/cycle/{slot % 7}; Secure",
            f"dupe{slot}=a; Path=/old; Path={path}; Domain=.bad-{site}; Domain=.{site}; SameSite=Bad; SameSite=Lax",
        ]
        if i >= 31 and i % 3 == 0:
            old_slot = (i - 31) % 31
            headers.append(f"cycle{old_slot}=gone; Domain=.{site}; Path=/cycle/{old_slot % 7}; Max-Age=0")
        if i % 5 == 0:
            headers.append(f"badps{i}=x; Domain={public_domain}; Secure")
        elif i % 7 == 0:
            headers.append(f"foreign{i}=x; Domain=.foreign-{site}; Secure")
        else:
            headers.append(f"token{slot}=t{i}; Path=/bucket; SameSite=None; Secure")
        if i % 11 == 0:
            headers.append(f"__Host-h{i}=bad; Domain=.{site}; Path=/; Secure")
        if i % 13 == 0:
            headers.append(f"__Secure-s{i}=bad; Path=/")
        rows.append({"type": "response", "id": f"r{i:04d}", "url": f"https://{host_name}{path}/set", "set_cookie": headers})

        req_host, req_site, _ = hosts[rng.randrange(len(hosts))]
        req_path = rng.choice([path, "/", f"/bucket/{rng.randrange(8)}/p{rng.randrange(5)}/view", f"/cycle/{rng.randrange(7)}/x"])
        same_site = req_site if rng.randrange(4) else rng.choice(["attacker.net", "other.pages.github.io", "example.com"])
        rows.append({
            "type": "request",
            "id": f"q{i:04d}",
            "url": f"{'http' if i % 17 == 0 else 'https'}://{req_host}{req_path}",
            "method": rng.choice(["GET", "POST", "get", "PUT"]),
            "top_level_site": same_site.upper() if i % 19 == 0 else same_site,
            "is_top_level_navigation": bool(rng.randrange(2)),
        })
        if i % 23 == 0:
            rows.append({
                "type": "request",
                "id": f"x{i:04d}",
                "url": f"https://other.example.com{req_path}",
                "method": "POST",
                "top_level_site": "attacker.net",
                "is_top_level_navigation": False,
            })
    write_jsonl(events, rows)
    actual = run_auditor(policy, events, timeout=100)
    expected = reference(policy, events)
    assert_equal(actual, expected)
    assert actual["summary"]["accepted"] > 1500
    assert actual["summary"]["set_cookie_rejected"] > 140
    assert actual["summary"]["deleted"] > 40
    assert actual["summary"]["truncated_requests"] > 120
    assert len(actual["domain_diagnostics"]) >= 8
    assert len(actual["cookie_lifecycle"]) > 700


def test_multi_seed_scope_churn_fuzz_batch_against_reference(tmp_path):
    """Verify several independent generated logs instead of one fixed randomized shape."""
    hosts = [
        ("app.example.com", "example.com", ".com"),
        ("static.example.com", "example.com", ".com"),
        ("shop.service.co.uk", "service.co.uk", ".co.uk"),
        ("api.service.co.uk", "service.co.uk", ".co.uk"),
        ("node.mesh.internal", "mesh.internal", ".internal"),
        ("app.team.pages.github.io", "team.pages.github.io", ".pages.github.io"),
    ]
    total_deleted = 0
    total_truncated = 0
    total_lifecycle = 0
    for seed in [811021, 811037, 811057]:
        rng = random.Random(seed)
        policy = tmp_path / f"policy_{seed}.json"
        events = tmp_path / f"events_{seed}.jsonl"
        policy.write_text(json.dumps({
            "public_suffixes": ["com", "net", "co.uk", "uk", "internal", "github.io", "pages.github.io"],
            "sensitive_name_patterns": ["session", "sid", "auth", "token", "secret"],
            "max_cookie_header_bytes": 45 + seed % 13,
        }), encoding="utf-8")
        rows = []
        for i in range(180):
            host_name, site, public_domain = hosts[(i + rng.randrange(len(hosts))) % len(hosts)]
            path = f"/s/{rng.randrange(6)}/d{rng.randrange(4)}"
            slot = (i * 7 + seed) % 41
            headers = [
                f"sid{slot}=h{i}; Path={path}; Secure; HttpOnly; SameSite={rng.choice(['Lax', 'Strict'])}",
                f"sid{slot}=d{i}; Domain=.{site}; Path={path}; Secure; HttpOnly; SameSite=Lax",
                f"auth{slot}=a{i}; Path=/s; SameSite=None; Secure",
                f"pref{slot}=p{i}; Domain=.wrong-{site}; Domain=.{site}; Path=/old; Path={path}; SameSite=Bad; SameSite=Lax",
            ]
            if i % 6 == 0:
                headers.append(f"short{slot}=v{i}; Domain=.{site}; Path=/short/{slot % 5}; Secure")
                headers.append(f"short{slot}=gone; Domain=.{site}; Path=/short/{slot % 5}; Max-Age=0")
            if i >= 12 and i % 4 == 0:
                old_slot = ((i - 12) * 7 + seed) % 41
                old_path = f"/s/{rng.randrange(6)}/d{rng.randrange(4)}"
                headers.append(f"sid{old_slot}=gone; Domain=.{site}; Path={old_path}; Max-Age=0")
            if i % 9 == 0:
                headers.append(f"bad{i}=x; Domain={public_domain}; Secure")
            elif i % 10 == 0:
                headers.append(f"__Secure-oops{i}=x; Path=/s")
            rows.append({"type": "response", "id": f"r{seed}_{i:03d}", "url": f"https://{host_name}{path}/set", "set_cookie": headers})
            req_host, req_site, _ = hosts[rng.randrange(len(hosts))]
            rows.append({
                "type": "request",
                "id": f"q{seed}_{i:03d}",
                "url": f"{'http' if i % 14 == 0 else 'https'}://{req_host}{rng.choice([path, '/s', '/', f'/s/{rng.randrange(6)}/d{rng.randrange(4)}/x'])}",
                "method": rng.choice(["GET", "POST", "get"]),
                "top_level_site": req_site if rng.randrange(5) else "attacker.net",
                "is_top_level_navigation": bool(rng.randrange(2)),
            })
        write_jsonl(events, rows)
        actual = run_auditor(policy, events, timeout=70)
        expected = reference(policy, events)
        assert_equal(actual, expected)
        assert actual["summary"]["accepted"] > 500
        assert actual["summary"]["set_cookie_rejected"] > 25
        total_deleted += actual["summary"]["deleted"]
        total_truncated += actual["summary"]["truncated_requests"]
        total_lifecycle += len(actual["cookie_lifecycle"])
    assert total_deleted > 5
    assert total_truncated > 90
    assert total_lifecycle > 650
