from difflib import SequenceMatcher
from typing import Any


def _leaf_name(path: str) -> str: return path.split(".")[-1].replace("[*]", "")
def _parent(path: str) -> str: return path.rsplit(".", 1)[0] if "." in path else "$"

def _jaccard(a, b):
    A, B = set(a), set(b)
    if not A and not B: return 1.0
    if not A or not B: return 0.0
    return len(A & B) / len(A | B)

def _name_similarity(a, b): return SequenceMatcher(None, a, b).ratio()

def score_rename(old_path: str, old: dict[str, Any], new_path: str, new: dict[str, Any]) -> float:
    fp = _jaccard(old.get("value_fingerprint", []), new.get("value_fingerprint", []))
    old_types, new_types = set(old.get("types", [])), set(new.get("types", []))
    scalar_coercible = old_types <= {"string","integer","number"} and new_types <= {"string","integer","number"}
    type_match = 1.0 if old_types == new_types or scalar_coercible else 0.0
    nullable = 1.0 if old.get("nullable") == new.get("nullable") else 0.0
    presence = 1.0 - min(abs(old.get("presence_rate", 0) - new.get("presence_rate", 0)), 1.0)
    name = _name_similarity(_leaf_name(old_path), _leaf_name(new_path))
    parent = 1.0 if _parent(old_path) == _parent(new_path) else 0.0
    return round(0.60*fp + 0.14*type_match + 0.08*nullable + 0.10*presence + 0.03*name + 0.05*parent, 6)


def diff(old_schema, new_schema, min_match=0.6):
    old_paths, new_paths = set(old_schema["paths"]), set(new_schema["paths"])
    common, removed, added = old_paths & new_paths, old_paths - new_paths, new_paths - old_paths
    changes = []
    for p in sorted(common):
        a, b = old_schema["paths"][p], new_schema["paths"][p]
        if set(a["types"]) != set(b["types"]):
            changes.append({"kind":"RETYPED","path":p,"old_types":a["types"],"new_types":b["types"]})
    candidates = sorted(((score_rename(o, old_schema["paths"][o], n, new_schema["paths"][n]), o, n) for o in removed for n in added), reverse=True)
    used_o, used_n = set(), set()
    for score, oldp, newp in candidates:
        if oldp in used_o or newp in used_n or score < min_match: continue
        used_o.add(oldp); used_n.add(newp)
        changes.append({"kind":"RENAMED","old":oldp,"new":newp,"confidence":score})
    changes += [{"kind":"REMOVED","path":p} for p in sorted(removed-used_o)]
    changes += [{"kind":"ADDED","path":p} for p in sorted(added-used_n)]
    return {"changes": changes}
