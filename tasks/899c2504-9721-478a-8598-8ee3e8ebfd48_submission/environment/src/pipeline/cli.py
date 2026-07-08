import argparse
from pathlib import Path

from .io import load_csv, load_lines, load_toml_text, write_json
from .logic import digest, drift, drift_details, is_idempotent, ownership_state, restart_plan


def _dedupe_ordered(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def run(stage: str, base: Path, output: Path, state: Path) -> None:
    files = load_csv(base / "data" / "files.csv")

    if stage == "m1":
        state_rules = load_toml_text(base / "config" / "state_rules.toml")
        rotation_epoch = state_rules["rotation_epoch"]
        actions = _dedupe_ordered(load_lines(base / "data" / "rotation_actions.txt"))
        targets = [r["path"] for r in files]
        write_json(
            output / "m1_plan.json",
            {
                "stage": "m1",
                "targets": targets,
                "target_count": len(targets),
                "rotation_epoch": rotation_epoch,
                "actions": actions,
            },
        )
        return

    ownership_rules = load_toml_text(base / "config" / "ownership_rules.toml")
    mode_rules = load_toml_text(base / "config" / "mode_rules.toml")
    owner = ownership_rules["required_owner"]
    group = ownership_rules["required_group"]
    mode = mode_rules["required_mode"]

    current = ownership_state(files)
    mismatches = drift(files, owner, group, mode)

    if stage == "m2":
        details = drift_details(files, owner, group, mode)
        write_json(
            output / "m2_permissions.json",
            {
                "stage": "m2",
                "ownership_state": current,
                "mode_state": {k: v["mode"] for k, v in current.items()},
                "drift": mismatches,
                "drift_details": details,
            },
        )
        return

    services = load_csv(base / "data" / "services.csv")
    service_rules = load_toml_text(base / "config" / "service_rules.toml")
    required_units = service_rules["required_units"]
    allowlist = set(load_lines(base / "data" / "units_allowlist.txt"))

    gated, blocked = restart_plan(services, required_units, allowlist)

    if stage == "m3":
        write_json(
            output / "m3_services.json",
            {
                "stage": "m3",
                "restart_plan": gated,
                "gated_units": gated,
                "blocked_units": blocked,
            },
        )
        return

    summary = {"blocked": len(blocked), "drift": len(mismatches), "gated": len(gated)}
    write_json(
        output / "m4_audit.json",
        {
            "stage": "m4",
            "idempotent": is_idempotent(len(mismatches), len(blocked)),
            "digest": digest(summary),
            "summary": summary,
        },
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stage", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--state", required=True)
    a = p.parse_args()
    run(a.stage, Path(a.base), Path(a.output), Path(a.state))


if __name__ == "__main__":
    main()
