"""
Evaluation metrics for validating predictions against gold truth and schema rules.
Used both for automated benchmarking and DSPy compiler teleprompter optimization.
"""

import re
import json

def parse_dollar_amount(val_str: str) -> float:
    try:
        clean = re.sub(r"[^\d.]", "", str(val_str))
        return float(clean) if clean else 0.0
    except Exception:
        return 0.0

def validate_schema(output_dict: dict) -> tuple[bool, list[str]]:
    """Checks if output strictly respects production API contract."""
    errors = []
    
    # Check required keys
    for req in ["verdict", "fraud_risk_score", "payout_amount"]:
        if req not in output_dict or output_dict[req] is None:
            errors.append(f"Missing field '{req}'")

    # Validate verdict enum
    verdict = str(output_dict.get("verdict", "")).strip().upper()
    if verdict not in ["APPROVE", "REJECT", "MANUAL_REVIEW"]:
        errors.append(f"Invalid verdict '{verdict}', must be APPROVE, REJECT, or MANUAL_REVIEW")

    # Validate fraud score range
    try:
        score = int(re.sub(r"[^\d]", "", str(output_dict.get("fraud_risk_score", "-1"))))
        if not (0 <= score <= 100):
            errors.append(f"Fraud score {score} out of [0, 100] range")
    except Exception:
        errors.append("Non-numeric fraud_risk_score")

    # Validate payout format
    payout = parse_dollar_amount(output_dict.get("payout_amount", ""))
    if verdict in ["REJECT", "MANUAL_REVIEW"] and payout > 0.0:
        errors.append(f"Rejected/Review claim cannot have positive payout (${payout})")

    return len(errors) == 0, errors

def dspy_metric(gold, pred, trace=None) -> float:
    """
    DSPy compiler metric. Returns a float between 0.0 and 1.0.
    Rewards correct verdict, proper formatting, and adherence to zero-payout constraints.
    """
    score = 0.0
    
    pred_verdict = str(getattr(pred, "verdict", "")).strip().upper()
    gold_verdict = str(getattr(gold, "verdict", "")).strip().upper()

    # 1. Exact verdict match (50% weight)
    if pred_verdict == gold_verdict:
        score += 0.5
    elif pred_verdict in ["APPROVE", "REJECT", "MANUAL_REVIEW"]:
        # Partial credit for generating a valid enum
        score += 0.1

    # 2. Schema adherence & payout validation (30% weight)
    try:
        pred_payout = parse_dollar_amount(getattr(pred, "payout_amount", "0"))
        if pred_verdict in ["REJECT", "MANUAL_REVIEW"]:
            if pred_payout == 0.0:
                score += 0.3
        else:
            if pred_payout > 0.0:
                score += 0.3
    except Exception:
        pass

    # 3. Valid fraud score range (20% weight)
    try:
        fscore = int(re.sub(r"[^\d]", "", str(getattr(pred, "fraud_risk_score", "-1"))))
        if 0 <= fscore <= 100:
            score += 0.2
    except Exception:
        pass

    return min(1.0, score)
