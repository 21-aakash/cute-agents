"""
DSPy Signatures defining the declarative contracts for the dispute agent.
"""

import dspy

class RefundDisputeSignature(dspy.Signature):
    """
    Evaluate customer refund dispute claims against corporate policy rules:
    - Standard return window is strictly <= 30 days.
    - VIP customers get extended return window <= 45 days.
    - Digital software, keys, downloads, and custom personalized merchandise are STRICTLY NON-REFUNDABLE (REJECT).
    - Damaged upon arrival within 48h qualifies for instant APPROVE with photo proof.
    - High-value claims (> $1,000) or missing/empty box allegations MUST be escalated to MANUAL_REVIEW.
    - If REJECT or MANUAL_REVIEW, payout_amount must be $0.00.
    """
    customer_tier = dspy.InputField(desc="Customer tier: Standard, VIP, or Flagged_Watchlist")
    order_type = dspy.InputField(desc="Category of product (Physical, Digital Software, Custom, etc.)")
    days_since_purchase = dspy.InputField(desc="Elapsed calendar days since order delivery")
    item_value = dspy.InputField(desc="Dollar monetary value of the disputed transaction")
    claim_text = dspy.InputField(desc="Customer's textual explanation or complaint message")

    rationale = dspy.OutputField(desc="Step-by-step policy constraint verification")
    verdict = dspy.OutputField(desc="Exact uppercase classification: APPROVE, REJECT, or MANUAL_REVIEW")
    fraud_risk_score = dspy.OutputField(desc="Numeric integer 0-100 estimating risk")
    payout_amount = dspy.OutputField(desc="Approved dollar refund amount (e.g. $85.00 or $0.00)")
