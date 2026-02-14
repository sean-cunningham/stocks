from jsonschema import validate
from jsonschema.exceptions import ValidationError


DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "rec": {"enum": ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]},
        "signal_score": {"type": "number", "minimum": 0, "maximum": 1},
        "prob_outperform_90d": {"type": "number", "minimum": 0, "maximum": 1},
        "horizon_days": {"type": "integer"},
        "key_drivers": {"type": "array", "items": {"type": "string"}},
        "key_risks": {"type": "array", "items": {"type": "string"}},
        "disconfirming_evidence": {"type": "array", "items": {"type": "string"}},
        "what_changed_since_last": {"type": "array", "items": {"type": "string"}},
        "exit_triggers": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "rec",
        "signal_score",
        "prob_outperform_90d",
        "horizon_days",
        "key_drivers",
        "key_risks",
        "disconfirming_evidence",
        "exit_triggers",
    ],
}


def validate_decision_payload(payload: dict) -> dict:
    try:
        validate(instance=payload, schema=DECISION_SCHEMA)
    except ValidationError as exc:
        raise ValueError(f"Invalid LLM decision payload: {exc.message}") from exc
    return payload
