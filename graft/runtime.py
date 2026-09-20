from pathlib import Path
from typing import Any
import json

from .mapping import apply_mapping, validate_mapping
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
