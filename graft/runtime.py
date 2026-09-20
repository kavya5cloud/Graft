from pathlib import Path
from typing import Any
import json
import os
import tempfile

from .mapping import apply_mapping, validate_mapping
from .healing import attempt_heal
from .inferencer import infer
from .provider import Provider


def load_active_mapping(root: Path, provider: str) -> dict:
    """Load the provider's atomically selected current mapping."""
    path = root / "mappings" / provider / "current.json"

    if not path.exists():
        raise FileNotFoundError(
            f"no active mapping for provider: {provider}"
        )

    mapping = json.loads(path.read_text())
    validate_mapping(mapping)
    return mapping


def normalize(body: Any, mapping: dict) -> dict:
    """Apply a Graft mapping to a provider response body."""
    validate_mapping(mapping)
    return apply_mapping(body, mapping)


def normalize_active(root: Path, provider: str, body: Any) -> dict:
    """Normalize a provider response using its active mapping."""
    mapping = load_active_mapping(root, provider)
    return normalize(body, mapping)


def fetch_and_normalize(
    root: Path,
    provider_name: str,
    provider: Provider,
    url: str,
) -> dict:
    """Fetch a provider response and normalize its body."""
    response = provider.fetch(url)
    mapping = load_active_mapping(root, provider_name)

    return {
        "status": response["status"],
        "headers": response["headers"],
        "data": normalize(response["body"], mapping),
    }



def activate_mapping(root: Path, provider: str, mapping: dict) -> Path:
    """Atomically activate a validated mapping."""
    validate_mapping(mapping)

    provider_dir = root / "mappings" / provider
    provider_dir.mkdir(parents=True, exist_ok=True)

    version = mapping["version"]
    version_path = provider_dir / f"v{version}.json"
    current_path = provider_dir / "current.json"

    version_path.write_text(
        json.dumps(mapping, indent=2, sort_keys=True)
    )

    fd, temp_name = tempfile.mkstemp(
        dir=provider_dir,
        prefix=".current-",
        suffix=".tmp",
    )

    try:
        with os.fdopen(fd, "w") as tmp:
            json.dump(mapping, tmp, indent=2, sort_keys=True)
            tmp.flush()
            os.fsync(tmp.fileno())

        os.replace(temp_name, current_path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise

    return version_path


def load_contract_schema(root: Path, provider: str, endpoint: str) -> dict:
    """Load the registered contract schema for a provider endpoint."""
    registry_path = root / ".graft" / "contracts.json"

    if not registry_path.exists():
        raise FileNotFoundError(
            f"no registered contract for {provider}/{endpoint}"
        )

    registry = json.loads(registry_path.read_text())
    contract = registry.get(f"{provider}/{endpoint}")

    if not contract:
        raise FileNotFoundError(
            f"no registered contract for {provider}/{endpoint}"
        )

    schema_path = Path(contract["schema"])

    if not schema_path.is_absolute():
        schema_path = root / schema_path

    if not schema_path.exists():
        raise FileNotFoundError(
            f"contract schema not found: {schema_path}"
        )

    return json.loads(schema_path.read_text())


def fetch_and_heal(
    root: Path,
    provider_name: str,
    endpoint: str,
    provider: Provider,
    url: str,
    invariants=None,
) -> dict:
    """Fetch, normalize, and safely heal deterministic provider drift."""
    response = provider.fetch(url)
    fixture = response

    old_schema = load_contract_schema(
        root,
        provider_name,
        endpoint,
    )

    new_schema = infer([fixture])

    mapping = load_active_mapping(
        root,
        provider_name,
    )

    result = attempt_heal(
        old_schema,
        new_schema,
        mapping,
        fixture,
        invariants or [],
    )

    if result["status"] == "healed":
        activate_mapping(
            root,
            provider_name,
            result["candidate"],
        )

        mapping = load_active_mapping(
            root,
            provider_name,
        )

    return {
        "status": response["status"],
        "headers": response["headers"],
        "data": normalize(response["body"], mapping),
        "healing": {
            "status": result["status"],
            "version": mapping["version"],
        },
    }
