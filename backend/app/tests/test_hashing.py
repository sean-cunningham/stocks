from app.hashing import canonical_json_hash


def test_canonical_json_hash_deterministic() -> None:
    a = {"b": 2, "a": 1, "nested": {"z": 1, "y": [3, 2, 1]}}
    b = {"nested": {"y": [3, 2, 1], "z": 1}, "a": 1, "b": 2}
    assert canonical_json_hash(a) == canonical_json_hash(b)
