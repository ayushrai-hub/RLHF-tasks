"""Endpoint tests for the change-request approval-routing service.

The server is started by test.sh and listens on BASE_URL (default :8080).
Every test creates its own change requests, so tests are independent.
"""
import os
import requests

BASE = os.environ.get("BASE_URL", "http://localhost:8080")
JSON = {"Content-Type": "application/json"}


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def mk(stages=None, title="Change", author="alice"):
    if stages is None:
        stages = [{"name": "review", "required": 1, "eligible": ["bob", "carol"]}]
    r = requests.post(f"{BASE}/change-requests", json={
        "title": title, "author": author, "stages": stages}, headers=JSON)
    assert r.status_code == 201, r.text
    return r.json()


def get(cid):
    r = requests.get(f"{BASE}/change-requests/{cid}")
    assert r.status_code == 200, r.text
    return r.json()


def approve(cid, who, decision="approve"):
    return requests.post(f"{BASE}/change-requests/{cid}/approvals",
                         json={"approver": who, "decision": decision}, headers=JSON)


def revoke(cid, who, version):
    return requests.delete(f"{BASE}/change-requests/{cid}/approvals/{who}",
                           headers={"If-Match": f'"{version}"'})


# a 3-stage pipeline, one approval needed per stage, distinct eligibles
PIPE3 = [
    {"name": "s0", "required": 1, "eligible": ["a", "z"]},
    {"name": "s1", "required": 1, "eligible": ["b", "z"]},
    {"name": "s2", "required": 1, "eligible": ["c", "z"]},
]


# ----------------------------------------------------------------------------
# basics
# ----------------------------------------------------------------------------
def test_healthz():
    r = requests.get(f"{BASE}/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_returns_derived_defaults():
    cr = mk()
    assert cr["status"] == "pending"
    assert cr["current_stage"] == 0
    assert cr["revision"] == 0
    assert cr["version"] == 1
    assert cr["approvals"] == []


def test_create_etag_header():
    r = requests.post(f"{BASE}/change-requests", json={
        "title": "x", "author": "a",
        "stages": [{"name": "s", "required": 1, "eligible": ["a"]}]}, headers=JSON)
    assert r.status_code == 201
    assert r.headers.get("ETag") == '"1"'


# ----------------------------------------------------------------------------
# create validation
# ----------------------------------------------------------------------------
def test_create_requires_title():
    r = requests.post(f"{BASE}/change-requests", json={
        "title": "", "author": "a",
        "stages": [{"name": "s", "required": 1, "eligible": ["a"]}]}, headers=JSON)
    assert r.status_code == 422


def test_create_requires_author():
    r = requests.post(f"{BASE}/change-requests", json={
        "title": "t", "author": "",
        "stages": [{"name": "s", "required": 1, "eligible": ["a"]}]}, headers=JSON)
    assert r.status_code == 422


def test_create_requires_at_least_one_stage():
    r = requests.post(f"{BASE}/change-requests", json={
        "title": "t", "author": "a", "stages": []}, headers=JSON)
    assert r.status_code == 422


def test_create_stage_required_must_be_positive():
    r = requests.post(f"{BASE}/change-requests", json={
        "title": "t", "author": "a",
        "stages": [{"name": "s", "required": 0, "eligible": ["a"]}]}, headers=JSON)
    assert r.status_code == 422


def test_create_stage_needs_eligible():
    r = requests.post(f"{BASE}/change-requests", json={
        "title": "t", "author": "a",
        "stages": [{"name": "s", "required": 1, "eligible": []}]}, headers=JSON)
    assert r.status_code == 422


def test_create_unsatisfiable_stage_rejected():
    # required exceeds the number of distinct eligible approvers
    r = requests.post(f"{BASE}/change-requests", json={
        "title": "t", "author": "a",
        "stages": [{"name": "s", "required": 3, "eligible": ["a", "b"]}]}, headers=JSON)
    assert r.status_code == 422


# ----------------------------------------------------------------------------
# strict JSON
# ----------------------------------------------------------------------------
def test_create_rejects_non_json_content_type():
    r = requests.post(f"{BASE}/change-requests",
                      data='{"title":"t","author":"a","stages":[]}',
                      headers={"Content-Type": "text/plain"})
    assert r.status_code == 415


def test_create_rejects_unknown_field():
    r = requests.post(f"{BASE}/change-requests", json={
        "title": "t", "author": "a", "color": "red",
        "stages": [{"name": "s", "required": 1, "eligible": ["a"]}]}, headers=JSON)
    assert r.status_code == 400


# ----------------------------------------------------------------------------
# get / list / pagination
# ----------------------------------------------------------------------------
def test_get_missing_is_404():
    assert requests.get(f"{BASE}/change-requests/nope_404").status_code == 404


def test_get_etag_header():
    cr = mk()
    r = requests.get(f"{BASE}/change-requests/{cr['id']}")
    assert r.headers.get("ETag") == f'"{cr["version"]}"'


def test_list_has_total_and_array():
    mk()
    r = requests.get(f"{BASE}/change-requests")
    body = r.json()
    assert isinstance(body["change_requests"], list)
    assert body["total"] >= 1


def test_list_pagination_no_overlap():
    for i in range(5):
        mk(title=f"pg{i}")
    p1 = requests.get(f"{BASE}/change-requests?page=1&limit=2").json()["change_requests"]
    p2 = requests.get(f"{BASE}/change-requests?page=2&limit=2").json()["change_requests"]
    assert len(p1) == 2 and len(p2) == 2
    ids1 = {c["id"] for c in p1}
    ids2 = {c["id"] for c in p2}
    assert ids1.isdisjoint(ids2)


def test_list_empty_filter_returns_array_not_null():
    r = requests.get(f"{BASE}/change-requests?status=approved&limit=1&page=999")
    body = r.json()
    assert body["change_requests"] == []


def test_list_status_filter():
    cr = mk()
    approve(cr["id"], "bob")  # single stage required=1 -> approved
    r = requests.get(f"{BASE}/change-requests?status=approved")
    ids = {c["id"] for c in r.json()["change_requests"]}
    assert cr["id"] in ids
    pend = requests.get(f"{BASE}/change-requests?status=pending")
    assert cr["id"] not in {c["id"] for c in pend.json()["change_requests"]}


def test_list_total_counts_all_not_page():
    base = requests.get(f"{BASE}/change-requests").json()["total"]
    mk()
    mk()
    mk()
    after = requests.get(f"{BASE}/change-requests?limit=1").json()
    assert after["total"] >= base + 3
    assert len(after["change_requests"]) == 1


# ----------------------------------------------------------------------------
# approval happy path / progression
# ----------------------------------------------------------------------------
def test_single_stage_approve_completes():
    cr = mk()
    r = approve(cr["id"], "bob")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
    assert r.json()["current_stage"] == 1


def test_quorum_requires_two_distinct():
    cr = mk(stages=[{"name": "s", "required": 2, "eligible": ["a", "b", "c"]}])
    r = approve(cr["id"], "a")
    assert r.json()["status"] == "pending"
    assert r.json()["current_stage"] == 0
    r = approve(cr["id"], "b")
    assert r.json()["status"] == "approved"


def test_duplicate_same_stage_rejected():
    cr = mk(stages=[{"name": "s", "required": 2, "eligible": ["a", "b"]}])
    approve(cr["id"], "a")
    r = approve(cr["id"], "a")
    assert r.status_code == 409


def test_multistage_advances_one_at_a_time():
    cr = mk(stages=PIPE3)
    assert approve(cr["id"], "a").json()["current_stage"] == 1
    assert approve(cr["id"], "b").json()["current_stage"] == 2
    final = approve(cr["id"], "c").json()
    assert final["status"] == "approved"
    assert final["current_stage"] == 3


def test_approval_for_wrong_stage_blocked_by_eligibility():
    # 'c' is only eligible at stage 2; at stage 0 the current stage is 0
    cr = mk(stages=PIPE3)
    r = approve(cr["id"], "c")  # c not eligible for stage 0
    assert r.status_code == 422


def test_ineligible_approver_rejected():
    cr = mk()
    r = approve(cr["id"], "stranger")
    assert r.status_code == 422


def test_bad_decision_rejected():
    cr = mk()
    r = approve(cr["id"], "bob", decision="maybe")
    assert r.status_code == 422


# ----------------------------------------------------------------------------
# rejection
# ----------------------------------------------------------------------------
def test_reject_terminates():
    cr = mk(stages=PIPE3)
    approve(cr["id"], "a")  # advance to stage 1
    r = approve(cr["id"], "b", decision="reject")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "rejected"
    assert body["rejected_by"] == "b"
    assert body["rejected_stage"] == 1
    assert body["current_stage"] == 1


def test_no_approval_after_reject():
    cr = mk(stages=PIPE3)
    approve(cr["id"], "a")
    approve(cr["id"], "b", decision="reject")
    r = approve(cr["id"], "z")
    assert r.status_code == 409


# ----------------------------------------------------------------------------
# the revoke cascade (rollback)
# ----------------------------------------------------------------------------
def test_revoke_requires_if_match():
    cr = mk()
    approve(cr["id"], "bob")
    r = requests.delete(f"{BASE}/change-requests/{cr['id']}/approvals/bob")
    assert r.status_code == 428


def test_revoke_version_mismatch():
    cr = mk()
    approve(cr["id"], "bob")
    r = revoke(cr["id"], "bob", 999)
    assert r.status_code == 412


def test_revoke_unknown_approver_404():
    cr = mk()
    v = get(cr["id"])["version"]
    r = revoke(cr["id"], "ghost", v)
    assert r.status_code == 404


def test_revoke_rolls_back_and_purges_later_stages():
    cr = mk(stages=PIPE3)
    approve(cr["id"], "a")  # stage0 done
    approve(cr["id"], "b")  # stage1 done
    approve(cr["id"], "c")  # approved
    cur = get(cr["id"])
    assert cur["status"] == "approved"
    r = revoke(cr["id"], "a", cur["version"])
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pending"
    assert body["current_stage"] == 0
    # b's and c's later-stage approvals must be discarded by the rollback
    active = requests.get(f"{BASE}/change-requests/{cr['id']}/approvals").json()["approvals"]
    assert active == []


def test_rollback_does_not_let_request_jump_ahead():
    cr = mk(stages=PIPE3)
    approve(cr["id"], "a")
    approve(cr["id"], "b")
    approve(cr["id"], "c")
    v = get(cr["id"])["version"]
    revoke(cr["id"], "a", v)
    # re-approve stage 0; the request must stop at stage 1 (needs a fresh
    # decision there) and must NOT vault back to approved on stale data
    r = approve(cr["id"], "a")
    assert r.json()["status"] == "pending"
    assert r.json()["current_stage"] == 1


def test_revoke_within_stage_drops_below_quorum():
    cr = mk(stages=[{"name": "s", "required": 2, "eligible": ["a", "b", "c"]}])
    approve(cr["id"], "a")
    approve(cr["id"], "b")  # approved
    v = get(cr["id"])["version"]
    r = revoke(cr["id"], "a", v)
    assert r.json()["status"] == "pending"
    assert r.json()["current_stage"] == 0


# ----------------------------------------------------------------------------
# edit resets approvals
# ----------------------------------------------------------------------------
def test_update_requires_if_match():
    cr = mk()
    r = requests.put(f"{BASE}/change-requests/{cr['id']}",
                     json={"title": "new"}, headers=JSON)
    assert r.status_code == 428


def test_update_version_mismatch():
    cr = mk()
    r = requests.put(f"{BASE}/change-requests/{cr['id']}",
                     json={"title": "new"}, headers={**JSON, "If-Match": '"99"'})
    assert r.status_code == 412


def test_update_resets_approvals_and_bumps_revision():
    cr = mk(stages=PIPE3)
    approve(cr["id"], "a")  # advance to stage 1
    v = get(cr["id"])["version"]
    r = requests.put(f"{BASE}/change-requests/{cr['id']}",
                     json={"title": "edited"}, headers={**JSON, "If-Match": f'"{v}"'})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "edited"
    assert body["revision"] == 1
    assert body["status"] == "pending"
    assert body["current_stage"] == 0
    assert body["approvals"] == []


def test_update_partial_keeps_stages():
    cr = mk(stages=PIPE3)
    v = cr["version"]
    r = requests.put(f"{BASE}/change-requests/{cr['id']}",
                     json={"title": "renamed"}, headers={**JSON, "If-Match": f'"{v}"'})
    assert len(r.json()["stages"]) == 3


def test_update_changing_stages_rechecks_validity():
    cr = mk()
    v = cr["version"]
    r = requests.put(f"{BASE}/change-requests/{cr['id']}",
                     json={"stages": [{"name": "s", "required": 5, "eligible": ["a"]}]},
                     headers={**JSON, "If-Match": f'"{v}"'})
    assert r.status_code == 422


# ----------------------------------------------------------------------------
# cancel
# ----------------------------------------------------------------------------
def test_cancel_terminates():
    cr = mk()
    r = requests.post(f"{BASE}/change-requests/{cr['id']}/cancel",
                      headers={"If-Match": f'"{cr["version"]}"'})
    assert r.status_code == 200
    assert r.json()["status"] == "canceled"


def test_cancel_requires_if_match():
    cr = mk()
    r = requests.post(f"{BASE}/change-requests/{cr['id']}/cancel")
    assert r.status_code == 428


def test_cancel_twice_conflicts():
    cr = mk()
    requests.post(f"{BASE}/change-requests/{cr['id']}/cancel",
                  headers={"If-Match": f'"{cr["version"]}"'})
    v = get(cr["id"])["version"]
    r = requests.post(f"{BASE}/change-requests/{cr['id']}/cancel",
                      headers={"If-Match": f'"{v}"'})
    assert r.status_code == 409


def test_no_approval_after_cancel():
    cr = mk()
    requests.post(f"{BASE}/change-requests/{cr['id']}/cancel",
                  headers={"If-Match": f'"{cr["version"]}"'})
    r = approve(cr["id"], "bob")
    assert r.status_code == 409


# ----------------------------------------------------------------------------
# approver rollup (cross-record)
# ----------------------------------------------------------------------------
def test_approver_active_and_lifetime():
    cr = mk(stages=[{"name": "s", "required": 2, "eligible": ["roll1", "roll2", "roll3"]}])
    approve(cr["id"], "roll1")
    a = requests.get(f"{BASE}/approvers/roll1").json()
    assert a["active_approvals"] == 1
    assert a["approvals_given"] == 1


def test_approver_lifetime_survives_revoke():
    cr = mk(stages=[{"name": "s", "required": 2, "eligible": ["lf1", "lf2", "lf3"]}])
    approve(cr["id"], "lf1")
    approve(cr["id"], "lf2")  # approved
    v = get(cr["id"])["version"]
    revoke(cr["id"], "lf1", v)
    a = requests.get(f"{BASE}/approvers/lf1").json()
    assert a["approvals_given"] == 1     # lifetime, never decremented
    assert a["active_approvals"] == 0     # but no longer active


def test_approver_pending_queue():
    cr = mk(stages=[{"name": "s", "required": 1, "eligible": ["pq1", "pq2"]}])
    a = requests.get(f"{BASE}/approvers/pq1").json()
    assert cr["id"] in a["pending_requests"]
    approve(cr["id"], "pq1")  # now approved, no longer pending for pq1
    a2 = requests.get(f"{BASE}/approvers/pq2").json()
    assert cr["id"] not in a2["pending_requests"]


def test_approver_lifetime_survives_delete():
    cr = mk(stages=[{"name": "s", "required": 1, "eligible": ["del1", "del2"]}])
    approve(cr["id"], "del1")
    requests.delete(f"{BASE}/change-requests/{cr['id']}")
    a = requests.get(f"{BASE}/approvers/del1").json()
    assert a["approvals_given"] == 1
    assert a["active_approvals"] == 0


# ----------------------------------------------------------------------------
# stats
# ----------------------------------------------------------------------------
def test_stats_created_survives_delete():
    before = requests.get(f"{BASE}/stats").json()["crs_created"]
    cr = mk()
    requests.delete(f"{BASE}/change-requests/{cr['id']}")
    after = requests.get(f"{BASE}/stats").json()["crs_created"]
    assert after == before + 1


def test_stats_active_excludes_terminal():
    cr = mk()
    before = requests.get(f"{BASE}/stats").json()["crs_active"]
    approve(cr["id"], "bob")  # approved -> terminal
    after = requests.get(f"{BASE}/stats").json()["crs_active"]
    assert after == before - 1


def test_stats_revokes_counter():
    before = requests.get(f"{BASE}/stats").json()["revokes_processed"]
    cr = mk(stages=[{"name": "s", "required": 2, "eligible": ["rv1", "rv2"]}])
    approve(cr["id"], "rv1")
    v = get(cr["id"])["version"]
    revoke(cr["id"], "rv1", v)
    after = requests.get(f"{BASE}/stats").json()["revokes_processed"]
    assert after == before + 1


# ----------------------------------------------------------------------------
# method routing / 405
# ----------------------------------------------------------------------------
def test_method_not_allowed_has_allow_header():
    r = requests.patch(f"{BASE}/change-requests")
    assert r.status_code == 405
    assert "GET" in r.headers.get("Allow", "")
    assert "POST" in r.headers.get("Allow", "")


def test_single_cr_method_not_allowed():
    cr = mk()
    r = requests.patch(f"{BASE}/change-requests/{cr['id']}")
    assert r.status_code == 405
    allow = r.headers.get("Allow", "")
    assert "PUT" in allow and "DELETE" in allow


def test_delete_returns_204_then_404():
    cr = mk()
    assert requests.delete(f"{BASE}/change-requests/{cr['id']}").status_code == 204
    assert requests.get(f"{BASE}/change-requests/{cr['id']}").status_code == 404


# ----------------------------------------------------------------------------
# approver groups (cross-record eligibility lever)
# ----------------------------------------------------------------------------
def mkgroup(members, name="grp"):
    r = requests.post(f"{BASE}/groups", json={"name": name, "members": members}, headers=JSON)
    assert r.status_code == 201, r.text
    return r.json()


def cr_with_group(gid, required, literal=None, title="grpcr"):
    stage = {"name": "s", "required": required, "eligible": literal or [], "eligible_groups": [gid]}
    r = requests.post(f"{BASE}/change-requests", json={
        "title": title, "author": "alice", "stages": [stage]}, headers=JSON)
    assert r.status_code == 201, r.text
    return r.json()


def group_get(gid):
    r = requests.get(f"{BASE}/groups/{gid}")
    assert r.status_code == 200, r.text
    return r.json()


def test_group_create_and_fields():
    g = mkgroup(["m1", "m2", "m3"])
    assert g["member_count"] == 3
    assert g["version"] == 1
    assert g["members"] == ["m1", "m2", "m3"]


def test_group_create_etag():
    r = requests.post(f"{BASE}/groups", json={"name": "g", "members": ["x"]}, headers=JSON)
    assert r.headers.get("ETag") == '"1"'


def test_group_requires_name_and_members():
    assert requests.post(f"{BASE}/groups", json={"name": "", "members": ["x"]}, headers=JSON).status_code == 422
    assert requests.post(f"{BASE}/groups", json={"name": "g", "members": []}, headers=JSON).status_code == 422


def test_stage_unknown_group_rejected():
    r = requests.post(f"{BASE}/change-requests", json={
        "title": "t", "author": "a",
        "stages": [{"name": "s", "required": 1, "eligible": [], "eligible_groups": ["grp_nope"]}]},
        headers=JSON)
    assert r.status_code == 422


def test_group_member_can_approve():
    g = mkgroup(["gm1", "gm2"])
    cr = cr_with_group(g["id"], 1)
    r = approve(cr["id"], "gm1")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_non_member_not_eligible_via_group():
    g = mkgroup(["gm1", "gm2"])
    cr = cr_with_group(g["id"], 1)
    r = approve(cr["id"], "outsider")
    assert r.status_code == 422


def test_unsatisfiable_against_group_membership():
    g = mkgroup(["u1", "u2"])
    # required 3 but only 2 distinct eligible (group members + no literals)
    r = requests.post(f"{BASE}/change-requests", json={
        "title": "t", "author": "a",
        "stages": [{"name": "s", "required": 3, "eligible": [], "eligible_groups": [g["id"]]}]},
        headers=JSON)
    assert r.status_code == 422


def test_group_quorum_counts_union_of_literal_and_members():
    g = mkgroup(["mem"])
    cr = cr_with_group(g["id"], 2, literal=["lit"])
    approve(cr["id"], "lit")
    r = approve(cr["id"], "mem")
    assert r.json()["status"] == "approved"


def test_group_update_requires_if_match():
    g = mkgroup(["a", "b"])
    r = requests.put(f"{BASE}/groups/{g['id']}", json={"members": ["a"]}, headers=JSON)
    assert r.status_code == 428


def test_group_update_version_mismatch():
    g = mkgroup(["a", "b"])
    r = requests.put(f"{BASE}/groups/{g['id']}", json={"members": ["a"]},
                     headers={**JSON, "If-Match": '"99"'})
    assert r.status_code == 412


def test_group_update_bumps_version():
    g = mkgroup(["a", "b", "c"])
    r = requests.put(f"{BASE}/groups/{g['id']}", json={"members": ["a", "b"]},
                     headers={**JSON, "If-Match": '"1"'})
    assert r.status_code == 200
    assert r.json()["version"] == 2
    assert r.json()["member_count"] == 2


def test_group_member_removal_reroutes_referencing_request():
    # the killer: a satisfied request drops back below quorum when the roster
    # that satisfied it loses a member, and the change is observed immediately
    g = mkgroup(["k1", "k2", "k3"])
    cr = cr_with_group(g["id"], 2)
    approve(cr["id"], "k1")
    approve(cr["id"], "k2")  # two distinct group members -> approved
    assert get(cr["id"])["status"] == "approved"
    # remove k2 from the group
    requests.put(f"{BASE}/groups/{g['id']}", json={"members": ["k1", "k3"]},
                 headers={**JSON, "If-Match": '"1"'})
    after = get(cr["id"])
    assert after["status"] == "pending"
    assert after["current_stage"] == 0


def test_group_member_readd_restores_routing():
    g = mkgroup(["r1", "r2", "r3"])
    cr = cr_with_group(g["id"], 2)
    approve(cr["id"], "r1")
    approve(cr["id"], "r2")
    requests.put(f"{BASE}/groups/{g['id']}", json={"members": ["r1", "r3"]},
                 headers={**JSON, "If-Match": '"1"'})
    assert get(cr["id"])["status"] == "pending"
    # add r2 back; the recorded approvals become effective again
    requests.put(f"{BASE}/groups/{g['id']}", json={"members": ["r1", "r2", "r3"]},
                 headers={**JSON, "If-Match": '"2"'})
    assert get(cr["id"])["status"] == "approved"


def test_group_delete_in_use_conflicts():
    g = mkgroup(["d1", "d2"])
    cr_with_group(g["id"], 1)
    r = requests.delete(f"{BASE}/groups/{g['id']}")
    assert r.status_code == 409


def test_group_delete_unused_succeeds():
    g = mkgroup(["x1"])
    assert requests.delete(f"{BASE}/groups/{g['id']}").status_code == 204
    assert requests.get(f"{BASE}/groups/{g['id']}").status_code == 404


def test_group_rollup_referencing_requests():
    g = mkgroup(["ref1", "ref2"])
    cr = cr_with_group(g["id"], 1)
    gv = group_get(g["id"])
    assert cr["id"] in gv["referencing_requests"]


def test_stats_groups_created_survives_delete():
    before = requests.get(f"{BASE}/stats").json()["groups_created"]
    g = mkgroup(["onlyme"])
    requests.delete(f"{BASE}/groups/{g['id']}")
    after = requests.get(f"{BASE}/stats").json()["groups_created"]
    assert after == before + 1


def test_group_method_not_allowed():
    r = requests.patch(f"{BASE}/groups")
    assert r.status_code == 405
    assert "POST" in r.headers.get("Allow", "")
