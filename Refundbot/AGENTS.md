# Agent Specification: Refundbot

## Role & Objective
Refundbot is an autonomous customer support and dispute resolution agent designed to evaluate refund requests against company policy, detect fraudulent signals, interact with order management databases, and make deterministic, compliant refund decisions.

---

## Architectural Paradigm: Tool-Augmented State Machine & Guardrails
* **Pattern**: Tool Calling + Policy Evaluation + Guardrail Interceptor
* **Core Agent Capabilities**:
  * **Order Lookup**: Queries order repository by `order_id` or customer email.
  * **Policy Compliance**: Validates return window (e.g. 30 days), item condition, and eligible product categories.
  * **Fraud Scoring**: Inspects customer refund history and velocity limits.
  * **Transaction Execution**: Dispatches automated refund webhooks / API calls upon approval or creates escalated human tickets.

---

## Tools & Integrations
| Tool Name | Type | Description |
|---|---|---|
| `get_order_details` | Data Fetch | Retrieves order date, item list, total amount, and delivery status |
| `evaluate_policy` | Rule Engine | Validates return eligibility against active store policies |
| `check_refund_history` | Fraud Engine | Calculates risk tier based on past return count |
| `process_refund` | Transaction | Triggers refund transaction via payment provider |
| `escalate_to_human` | Fallback | Escalates ambiguous or high-value cases to support reps |

---

## Execution & Testing
```bash
# Run tests
pytest tests/

# Start local server
uvicorn app.main:app --reload --port 8000
```
