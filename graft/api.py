from pathlib import Path
from typing import Any

from .provider import get_provider
from .runtime import fetch_and_normalize


class Graft:
    """Public API for normalized provider requests."""

    def __init__(self, root: Path | None = None):
        self.root = Path(root or Path.cwd())

    def request(
        self,
        provider: str,
        url: str,
        transport: str = "http",
    ) -> dict[str, Any]:
        """Fetch a provider response and normalize it."""
        client = get_provider(transport)

        return fetch_and_normalize(
            self.root,
            provider,
            client,
            url,
        )
