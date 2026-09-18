import json
from pathlib import Path


def register_contract(root, provider, endpoint, schema_path):
    root = Path(root)
    registry_path = root / ".graft" / "contracts.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    else:
        registry = {}

    key = f"{provider}/{endpoint}"
    registry[key] = {
        "provider": provider,
        "endpoint": endpoint,
        "schema": str(schema_path),
    }

    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return registry_path
