from abc import ABC, abstractmethod
import json
import urllib.request
from typing import Any


class Provider(ABC):
    @abstractmethod
    def fetch(self, url: str) -> dict[str, Any]:
        raise NotImplementedError


class HTTPProvider(Provider):
    def fetch(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, method="GET")

        with urllib.request.urlopen(request) as response:
            return {
                "status": response.status,
                "headers": dict(response.headers),
                "body": json.loads(response.read()),
            }
