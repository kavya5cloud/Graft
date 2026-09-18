import json
from datetime import datetime, timezone
from pathlib import Path


def record_audit(root, action, provider, **details):
    path = Path(root) / ".graft" / "audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "provider": provider,
        **details,
    }

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
