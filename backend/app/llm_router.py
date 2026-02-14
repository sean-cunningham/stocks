from app.llm_contract import validate_decision_payload


def llm_decide_from_evidence(evidence_packet: dict) -> dict:
    # TODO: Implement real LLM provider routing and model call.
    momentum = evidence_packet.get("price_momentum_20d", 0.0)
    vol = evidence_packet.get("vol_20d", 0.0)
    news_sentiment = evidence_packet.get("news_sentiment", 0.0)

    signal_score = max(0.0, min(1.0, 0.55 + momentum * 2.0 + news_sentiment * 0.2 - vol))
    prob_outperform = max(0.0, min(1.0, 0.50 + momentum + news_sentiment * 0.25))

    if signal_score >= 0.80 and prob_outperform >= 0.60:
        rec = "STRONG_BUY"
    elif signal_score >= 0.70 and prob_outperform >= 0.55:
        rec = "BUY"
    elif signal_score < 0.40:
        rec = "SELL"
    else:
        rec = "HOLD"

    decision = {
        "rec": rec,
        "signal_score": round(signal_score, 4),
        "prob_outperform_90d": round(prob_outperform, 4),
        "horizon_days": 90,
        "key_drivers": [
            "Price trend over last 20 sessions",
            "Recent headline flow balance",
        ],
        "key_risks": [
            "Macro shock could reverse momentum",
            "Guidance uncertainty remains",
        ],
        "disconfirming_evidence": [
            "Momentum can mean-revert quickly",
        ],
        "what_changed_since_last": evidence_packet.get("what_changed_since_last", []),
        "exit_triggers": [
            "Signal score drops below 0.70",
            "ATR trailing stop is hit",
        ],
    }
    return validate_decision_payload(decision)
