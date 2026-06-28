"""Dispatch milestone-specific verifier tests for the MSBuild audit task."""

from __future__ import annotations

import os


def _selected_milestone() -> str | None:
    for name in (
        "MILESTONE",
        "HARBOR_MILESTONE",
        "TERMINUS_MILESTONE",
        "CURRENT_MILESTONE",
        "STEP_NAME",
        "TASK_MILESTONE",
    ):
        value = os.environ.get(name, "").strip().lower()
        if not value:
            continue
        if value.startswith("milestone_"):
            return value.rsplit("_", 1)[-1]
        if value.startswith("m") and value[1:].isdigit():
            return value[1:]
        if value.isdigit():
            return value
    if os.environ.get("ALL_MILESTONES", "").strip() == "1":
        return None
    return "5"


_MILESTONE = _selected_milestone()

if _MILESTONE in {None, "1"}:
    from test_m1 import *  # noqa: F401,F403
if _MILESTONE in {None, "2"}:
    from test_m2 import *  # noqa: F401,F403
if _MILESTONE in {None, "3"}:
    from test_m3 import *  # noqa: F401,F403
if _MILESTONE in {None, "4"}:
    from test_m4 import *  # noqa: F401,F403
if _MILESTONE in {None, "5"}:
    from test_m5 import *  # noqa: F401,F403
