"""
Curated test and training datasets for Refund & Fraud Dispute Policy Engine.
Contains:
1. Training Set (for DSPy Teleprompter compilation)
2. Standard Evaluation Set
3. Drifted / Edge Case Set (representing real-world production shift)
"""

import dspy

# Training examples with gold standards for DSPy BootstrapFewShot
TRAIN_SET = [
    dspy.Example(
        customer_tier="Standard",
        order_type="Physical Apparel",
        days_since_purchase="12",
        item_value="$85.00",
        claim_text="Size too small, unworn with original tags attached.",
        verdict="APPROVE",
        fraud_risk_score="12",
        payout_amount="$85.00",
        policy_rationale="Standard customer returned unworn apparel within 30-day policy window."
    ).with_inputs("customer_tier", "order_type", "days_since_purchase", "item_value", "claim_text"),

    dspy.Example(
        customer_tier="Standard",
        order_type="Digital Software License",
        days_since_purchase="3",
        item_value="$120.00",
        claim_text="Downloaded software key and activated it, but decided I do not need it anymore.",
        verdict="REJECT",
        fraud_risk_score="45",
        payout_amount="$0.00",
        policy_rationale="Digital software keys are non-refundable once accessed or activated under Clause 4.2."
    ).with_inputs("customer_tier", "order_type", "days_since_purchase", "item_value", "claim_text"),

    dspy.Example(
        customer_tier="Standard",
        order_type="Electronics",
        days_since_purchase="38",
        item_value="$350.00",
        claim_text="Headphones stopped working yesterday. Want full refund.",
        verdict="REJECT",
        fraud_risk_score="30",
        payout_amount="$0.00",
        policy_rationale="Exceeds the 30-day standard return window. Refer customer to manufacturer warranty."
    ).with_inputs("customer_tier", "order_type", "days_since_purchase", "item_value", "claim_text"),

    dspy.Example(
        customer_tier="VIP",
        order_type="Electronics",
        days_since_purchase="39",
        item_value="$220.00",
        claim_text="Noise cancelling speaker defective. Unopened box condition.",
        verdict="APPROVE",
        fraud_risk_score="15",
        payout_amount="$220.00",
        policy_rationale="VIP loyalty tier qualifies for extended 45-day return window."
    ).with_inputs("customer_tier", "order_type", "days_since_purchase", "item_value", "claim_text"),

    dspy.Example(
        customer_tier="Standard",
        order_type="Physical Hardware",
        days_since_purchase="1",
        item_value="$890.00",
        claim_text="Box arrived crushed and internal screen is shattered. Attached photo proof.",
        verdict="APPROVE",
        fraud_risk_score="10",
        payout_amount="$890.00",
        policy_rationale="Damaged on arrival reported within 48-hour delivery window with photographic proof."
    ).with_inputs("customer_tier", "order_type", "days_since_purchase", "item_value", "claim_text"),

    dspy.Example(
        customer_tier="Flagged_Watchlist",
        order_type="Luxury Watch",
        days_since_purchase="5",
        item_value="$1450.00",
        claim_text="Claiming package was empty upon doorstep delivery.",
        verdict="MANUAL_REVIEW",
        fraud_risk_score="88",
        payout_amount="$0.00",
        policy_rationale="High-value dispute on a watchlist-flagged account requires human investigator review."
    ).with_inputs("customer_tier", "order_type", "days_since_purchase", "item_value", "claim_text"),
]

# Standard test set representing normal operational baseline
STANDARD_TEST_SET = [
    {
        "id": "std_1",
        "customer_tier": "Standard",
        "order_type": "Home Kitchen",
        "days_since_purchase": "18",
        "item_value": "$65.00",
        "claim_text": "Blender blade was missing from retail box. Item never used.",
        "expected_verdict": "APPROVE",
        "expected_payout": "$65.00",
        "policy_rule": "Missing components within 30-day window qualifies for full refund."
    },
    {
        "id": "std_2",
        "customer_tier": "Standard",
        "order_type": "Digital Gift Card",
        "days_since_purchase": "2",
        "item_value": "$50.00",
        "claim_text": "Bought wrong store gift card, code already revealed.",
        "expected_verdict": "REJECT",
        "expected_payout": "$0.00",
        "policy_rule": "Digital vouchers and gift cards are strictly non-refundable once viewed."
    },
    {
        "id": "std_3",
        "customer_tier": "VIP",
        "order_type": "Designer Bag",
        "days_since_purchase": "41",
        "item_value": "$420.00",
        "claim_text": "Color does not match photo. Completely unused with security seal intact.",
        "expected_verdict": "APPROVE",
        "expected_payout": "$420.00",
        "policy_rule": "VIP tier 45-day policy grace period applies to sealed luxury goods."
    },
    {
        "id": "std_4",
        "customer_tier": "Standard",
        "order_type": "Gaming Console",
        "days_since_purchase": "32",
        "item_value": "$499.00",
        "claim_text": "Console is fine, but I decided I want to save money.",
        "expected_verdict": "REJECT",
        "expected_payout": "$0.00",
        "policy_rule": "Standard 30-day window expired by 2 days; remorse return rejected."
    }
]

# Production Drift / Edge Case Set:
# Real world messy queries: slang, colloquialisms, ambiguous wording, borderline constraints, negative trap clauses
DRIFTED_EDGE_SET = [
    {
        "id": "drift_1",
        "customer_tier": "Standard",
        "order_type": "Digital Enterprise License Key (E-Book & Software)",
        "days_since_purchase": "1",
        "item_value": "$320.00",
        "claim_text": "hey bro i downloaded it 2 hours ago but my mac wont run it so cancel this and refund asap plzz!!",
        "expected_verdict": "REJECT",
        "expected_payout": "$0.00",
        "policy_rule": "Digital downloads activated are strictly non-refundable despite customer distress."
    },
    {
        "id": "drift_2",
        "customer_tier": "Standard",
        "order_type": "Custom Printed T-Shirt & Hoodie",
        "days_since_purchase": "4",
        "item_value": "$110.00",
        "claim_text": "i put my own family photo on this shirt but it looks kinda weird on me. take it back.",
        "expected_verdict": "REJECT",
        "expected_payout": "$0.00",
        "policy_rule": "Personalized/custom merchandise is strictly exempt from return policy unless factory damaged."
    },
    {
        "id": "drift_3",
        "customer_tier": "VIP",
        "order_type": "Smart Watch Series 9",
        "days_since_purchase": "44",
        "item_value": "$399.00",
        "claim_text": "Been travelling for 6 weeks, battery drains in 3 hours. Still under VIP 45-day window right?",
        "expected_verdict": "APPROVE",
        "expected_payout": "$399.00",
        "policy_rule": "VIP tier is 44 days (<= 45 days), defect covered under VIP extended window."
    },
    {
        "id": "drift_4",
        "customer_tier": "Standard",
        "order_type": "Precious Gold Pendant",
        "days_since_purchase": "14",
        "item_value": "$1950.00",
        "claim_text": "Driver tossed it over fence, box was empty! Give me my two thousand dollars right now!",
        "expected_verdict": "MANUAL_REVIEW",
        "expected_payout": "$0.00",
        "policy_rule": "Claims over $1,000 with alleged stolen/empty delivery require escalation to human investigator."
    }
]
