from .differ import diff
from .healer import propose
from .validator import validate


REPAIRABLE = frozenset({
    "RENAMED",
    "MOVED",
    "RETYPED",
})


def attempt_heal(old_schema, new_schema, current_mapping, fixture, invariants=None):
    """Attempt a deterministic, validated mapping repair."""
    drift = diff(old_schema, new_schema)

    if not drift["changes"]:
        return {
            "status": "no_drift",
            "drift": drift,
            "candidate": None,
            "validation": None,
        }

    if not any(
        change["kind"] in REPAIRABLE
        for change in drift["changes"]
    ):
        return {
            "status": "unsafe",
            "drift": drift,
            "candidate": None,
            "validation": None,
        }

    candidate = propose(
        current_mapping,
        drift,
        old_schema,
        new_schema,
    )

    validation = validate(
        current_mapping,
        candidate,
        [fixture],
        invariants or [],
    )

    if not validation["valid"]:
        return {
            "status": "rejected",
            "drift": drift,
            "candidate": candidate,
            "validation": validation,
        }

    return {
        "status": "healed",
        "drift": drift,
        "candidate": candidate,
        "validation": validation,
    }
