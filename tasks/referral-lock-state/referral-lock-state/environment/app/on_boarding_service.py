from __future__ import annotations

from typing import Any


def compute_threshold_lock_state(onboarding: dict[str, Any], config: dict[str, Any]) -> dict[str, bool]:
    referral_target = int(config.get("requiredReferralCount", 0) or 0)
    referral_count = int((onboarding.get("referralData") or {}).get("referralCount", 0) or 0)
    pdf_limit = int(config.get("downloadThresholdCount", 0) or 0)
    sim_limit = int(config.get("simulationViewCount", 0) or 0)
    mind_limit = int(config.get("mindmapViewCount", 0) or 0)
    pdf_uses = int(onboarding.get("pdfDownloadCount", 0) or 0)
    sim_uses = int(onboarding.get("simulationViewCount", 0) or 0)
    mind_uses = int(onboarding.get("mindmapViewCount", 0) or 0)

    referrals_met = referral_target > 0 and referral_count > referral_target
    if referrals_met:
        return {
            "pdfBankLocked": False,
            "simulationsLocked": sim_uses >= sim_limit,
            "mindmapsLocked": mind_uses >= mind_limit,
        }

    return {
        "pdfBankLocked": pdf_limit > 0 and pdf_uses > pdf_limit,
        "simulationsLocked": sim_limit > 0 and sim_uses > sim_limit,
        "mindmapsLocked": mind_limit > 0 and mind_uses > mind_limit,
    }


def build_report(config: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    records = []
    for row in sorted(rows, key=lambda item: item["userId"]):
        state = compute_threshold_lock_state(row, config)
        records.append({"userId": row["userId"], **state})
    return {"records": records}
