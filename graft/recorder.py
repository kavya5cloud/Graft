import hashlib, json, time
from pathlib import Path
from typing import Any, Mapping


def record_pair(root, provider, endpoint, request: Mapping[str,Any], response: Mapping[str,Any]):
    endpoint_key=endpoint.strip("/").replace("/","_") or "root"
    payload={"request":dict(request),"status":response.get("status"),"headers":dict(response.get("headers",{})),"body":response.get("body"),"timestamp":response.get("timestamp",time.time())}
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); digest=hashlib.sha256(raw).hexdigest()[:16]
    path=Path(root)/"fixtures"/provider/endpoint_key/f"{digest}.json"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,indent=2,sort_keys=True)); return path
