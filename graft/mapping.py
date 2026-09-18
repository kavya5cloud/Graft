import datetime as dt
import re
from decimal import Decimal
from typing import Any

TRANSFORMS = frozenset({"identity", "to_decimal", "to_int", "to_string", "iso_datetime", "unix_to_iso"})
DEFAULT_RE = re.compile(r"^default\((.*)\)$")


def _tokens(path: str):
    if path == "$":
        return []

    if not isinstance(path, str) or not path.startswith("$."):
        raise ValueError(f"Unsupported path: {path}")

    tokens = path[2:].split(".")

    if any(
        not token
        or token == "[*]"
        or token.count("[*]") > 1
        or ("[" in token and not token.endswith("[*]"))
        or ("]" in token and not token.endswith("[*]"))
        for token in tokens
    ):
        raise ValueError(f"Unsupported path: {path}")

    return tokens


def get_path(obj: Any, path: str) -> Any:
    tokens = _tokens(path)
    def walk(cur, i):
        if i == len(tokens): return cur
        token = tokens[i]
        if token.endswith("[*]"):
            key = token[:-3]
            seq = cur.get(key, []) if isinstance(cur, dict) else []
            if not isinstance(seq, list): return None
            return [walk(item, i+1) for item in seq]
        if not isinstance(cur, dict) or token not in cur: return None
        return walk(cur[token], i+1)
    return walk(obj, 0)


def _transform(value, name):
    if name.startswith("default(") and name.endswith(")"):
        return value if value is not None else name[8:-1]
    if name not in TRANSFORMS: raise ValueError(f"Unknown transform: {name}")
    if value is None: return None
    if name == "identity": return value
    if name == "to_decimal": return str(Decimal(str(value)))
    if name == "to_int": return int(value)
    if name == "to_string": return str(value)
    if name == "iso_datetime": return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
    if name == "unix_to_iso": return dt.datetime.fromtimestamp(float(value), tz=dt.timezone.utc).isoformat()


def validate_mapping(mapping):
    if not isinstance(mapping.get("version"), int) or not isinstance(mapping.get("fields"), dict): raise ValueError("Invalid mapping document")
    for name, spec in mapping["fields"].items():
        if not isinstance(spec, dict) or "path" not in spec: raise ValueError(f"Missing path for {name}")
        _tokens(spec["path"])
        transform = spec.get("transform", "identity")
        if transform not in TRANSFORMS and not DEFAULT_RE.fullmatch(transform): raise ValueError(f"Unknown transform: {transform}")


def apply_mapping(body, mapping):
    validate_mapping(mapping)
    return {name: _transform(get_path(body, spec["path"]), spec.get("transform", "identity")) for name, spec in mapping["fields"].items()}
