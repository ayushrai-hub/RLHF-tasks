"""Load all rule modules to populate the registry."""


def load_all() -> None:
    from task_audit.rules import (  # noqa: F401
        anti_cheat,
        difficulty,
        environment,
        instruction,
        metadata,
        milestones,
        oracle,
        rubrics,
        structure,
        verifiers,
    )
