import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

MAX_FINGERPRINT = 1000


def _type(v: Any) -> str:
    if v is None: return "null"
    if isinstance(v, bool): return "boolean"
    if isinstance(v, int) and not isinstance(v, bool): return "integer"
    if isinstance(v, float): return "number"
    if isinstance(v, str): return "string"
    if isinstance(v, dict): return "object"
    if isinstance(v, list): return "array"
    return "unknown"


def _fingerprint_value(v: Any) -> str:
    # Canonical scalar text deliberately ignores JSON scalar representation.
    # Thus "42.50" and 42.50 can still corroborate a rename+retype.
    if isinstance(v, bool): canonical = "bool:" + str(v).lower()
    elif v is None: canonical = "null"
    elif isinstance(v, (int, float)) and not isinstance(v, bool): canonical = "scalar:" + format(float(v), ".15g")
    elif isinstance(v, str): canonical = "scalar:" + v
    else: canonical = json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _walk(value: Any, path: str, out: dict[str, dict], present: set[str], counts: dict[str, int] | None = None) -> None:
    rec = out.setdefault(path, {"types": set(), "nulls": 0, "occurrences": 0, "fingerprints": set()})
    rec["types"].add(_type(value)); rec["occurrences"] += 1
    present.add(path)
    if counts is not None:
        counts[path] = counts.get(path, 0) + 1
    if value is None:
        rec["nulls"] += 1; return
    if isinstance(value, dict):
        for k, child in value.items(): _walk(child, f"{path}.{k}" if path != "$" else f"$.{k}", out, present, counts)
    elif isinstance(value, list):
        item_path = f"{path}[*]"
        if not value: out.setdefault(item_path, {"types": set(), "nulls": 0, "occurrences": 0, "fingerprints": set()})
        for child in value: _walk(child, item_path, out, present, counts)
    else:
        if len(rec["fingerprints"]) < MAX_FINGERPRINT: rec["fingerprints"].add(_fingerprint_value(value))


def infer(fixtures: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(fixtures); n = max(len(rows), 1)
    aggregate: dict[str, dict] = {}; presence = defaultdict(int)
    for row in rows:
        seen: set[str] = set()
        _walk(row.get("body"), "$", aggregate, seen)
        for p in seen: presence[p] += 1
    paths = {}
    for p, r in sorted(aggregate.items()):
        if p == "$":
            denominator = 1
            numerator = 1
        elif "[*]" in p:
            wildcard_end = p.find("[*]") + 3
            array_item_path = p[:wildcard_end]
            denominator = aggregate.get(array_item_path, {}).get("occurrences", 0)
            numerator = r["occurrences"]
        else:
            denominator = n
            numerator = presence[p]

        rate = numerator / denominator if denominator else 0.0

        paths[p] = {
            "types": sorted(r["types"]),
            "nullable": "null" in r["types"],
            "presence_rate": round(rate, 6),
            "value_fingerprint": sorted(r["fingerprints"])[:MAX_FINGERPRINT],
        }
    return {"version": 1, "fixture_count": len(rows), "paths": paths}


def load_fixtures(directory: str | Path) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(directory).glob("*.json"))]
