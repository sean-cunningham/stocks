def canonical_json_hash(obj: dict) -> str:
    import hashlib
    import json

    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
