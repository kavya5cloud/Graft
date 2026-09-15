from copy import deepcopy
from .mapping import validate_mapping


def _coercion(old_types, new_types):
    old, new = set(old_types), set(new_types)
    if old == new: return "identity"
    if "string" in old and ("number" in new or "integer" in new): return "to_decimal"
    if "integer" in old and "string" in new: return "to_string"
    if "number" in old and "string" in new: return "to_decimal"
    if "integer" in old and "number" in new: return "to_decimal"
    return "identity"


def propose(old_mapping, diff_result, old_schema, new_schema):
    candidate = deepcopy(old_mapping); candidate["version"] = old_mapping.get("version", 1) + 1
    for change in diff_result["changes"]:
        if change["kind"] == "RENAMED" and change["confidence"] >= 0.9:
            for field, spec in candidate["fields"].items():
                if spec.get("path") == change["old"]:
                    spec["path"] = change["new"]
                    old_types = old_schema["paths"][change["old"]]["types"]
                    new_types = new_schema["paths"][change["new"]]["types"]
                    coercion = _coercion(old_types, new_types)
                    if coercion != "identity": spec["transform"] = coercion
        elif change["kind"] == "RETYPED":
            p = change["path"]
            for spec in candidate["fields"].values():
                if spec.get("path") == p: spec["transform"] = _coercion(old_schema["paths"][p]["types"], new_schema["paths"][p]["types"])
    validate_mapping(candidate)
    return candidate
