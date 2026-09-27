## 🎯 **Production-Ready Refundbot: Complete Implementation Roadmap**

Based on your requirements, here's the **prioritized TODO list** to transform this into a production-grade agentic system:

---

## **Phase 1: Long-Running Agent with Checkpoints** (Foundation for everything else)
*Google Vertex AI Reasoning Engine pattern - checkpoint persistence & resume*

### **P0 Tasks** (Critical - 8-10 hours)

#### 1.1 Checkpoint System Architecture
```
✅ Create app/checkpoints/checkpoint_manager.py
- Store agent state: current_step, completed_steps, pending_actions, context
- SQLite table: agent_checkpoints (checkpoint_id, conversation_id, state, created_at, resumed_at)
- Methods: save_checkpoint(), load_checkpoint(), resume_from_checkpoint()
```

#### 1.2 Waiting States & Resume Logic
```
✅ Modify app/agent.py to support pause/resume
- Add agent states: RUNNING, WAITING_REFUND_STATUS, WAITING_RETURN_SHIPMENT, WAITING_ADMIN_APPROVAL, WAITING_PHOTO_UPLOAD
- When agent needs to wait:
  1. Save checkpoint with current state
  2. Return status: "waiting_for": "admin_approval", "checkpoint_id": "xyz"
  3. Expose resume endpoint: POST /agent/resume/{checkpoint_id}
```

#### 1.3 Human-in-the-Loop Approval System
```
✅ Create app/approvals/approval_manager.py
- SQLite table: approval_requests (id, checkpoint_id, request_type, details, status, admin_response, created_at)
- Admin dashboard: static/admin.html
- Endpoints:
  - GET /admin/pending-approvals
  - POST /admin/approve/{approval_id}
  - POST /admin/reject/{approval_id}
```

#### 1.4 External Status Polling (Refund/Return Tracking)
```
✅ Create app/trackers/status_tracker.py
- Background task (asyncio loop) checks:
  - Refund processing status (external payment gateway)
  - Return shipment tracking (shipping carrier API)
- When status changes → resume checkpoint
- Store in: external_status_tracking table
```

---

## **Phase 2: Image Analysis for Return Eligibility** (Visual verification)

### **P0 Tasks** (Critical - 6-8 hours)

#### 2.1 Photo Upload & Storage
```
✅ Add endpoint: POST /upload-return-photo
- Accept multipart/form-data with image
- Store in: ./uploads/return_photos/{order_id}_{timestamp}.jpg
- Save metadata: return_photos table (photo_id, order_id, filepath, uploaded_at, analysis_status)
```

#### 2.2 Vision API Integration (OpenAI GPT-4 Vision / Claude Vision)
```
✅ Create app/vision/damage_assessor.py
- analyze_return_condition(image_path) -> {
    "eligible": bool,
    "condition": "pristine|minor_wear|damaged|severely_damaged",
    "damage_details": str,
    "confidence": 0.0-1.0
  }
- Use prompt: "Analyze this product return image. Check for: original packaging, product condition, damage, signs of use. Determine if eligible for full refund."
```

#### 2.3 Agent Tool Integration
```
✅ Add tool: request_return_photo(order_id, item_id)
- Saves checkpoint with state: WAITING_PHOTO_UPLOAD
- Returns: "Please upload a photo of the item. Upload at: [URL]"
- POST /upload-return-photo triggers resume
```

#### 2.4 Conditional Refund Logic
```
✅ Modify process_refund() tool:
- If item requires photo verification → request_return_photo()
- On photo upload → analyze_return_condition()
- If condition == "damaged" → escalate or partial refund
- If condition == "pristine" → approve full refund
```

---

## **Phase 3: LLM-as-Judge Evaluation System** (Quality assurance)

### **P0 Tasks** (Critical - 5-6 hours)

#### 3.1 Test Case Library
```
✅ Create tests/eval/test_cases.json
[
  {
    "id": "TC001",
    "user_query": "I want a refund for order ORD001",
    "expected_tool": "process_refund",
    "expected_outcome": "refund_approved",
    "expected_policy_check": true
  },
  {
    "id": "TC002",
    "user_query": "What's the capital of France?",
    "expected_outcome": "out_of_scope"
  },
  // ... 50+ test cases
]
```

#### 3.2 LLM-as-Judge Implementation
```
✅ Create tests/eval/llm_judge.py
- evaluate_response(query, agent_response, expected_outcome) -> {
    "score": 0-10,
    "reasoning": str,
    "passed": bool,
    "issues": []
  }
- Judge prompt: "Rate this agent response on: correctness, policy compliance, tone, completeness"
```

#### 3.3 Automated Eval Runner
```
✅ Create tests/eval/run_eval.py
- Run all test cases through agent
- Collect: tool_used, response, tokens, latency
- Judge each response
- Generate report: eval_report_{timestamp}.json
- Metrics: pass_rate, avg_score, tool_accuracy, policy_compliance_rate
```

#### 3.4 Regression Testing
```
✅ Add pytest tests: tests/test_agent_regression.py
- Test critical flows: refund approval, out-of-scope, guardrails
- Mock LLM responses for deterministic tests
- CI/CD integration (GitHub Actions)
```

---

## **Phase 4: Intent Detection & Router Agent** (Multi-agent orchestration)

### **P1 Tasks** (High priority - 6-8 hours)

#### 4.1 Intent Classifier
```
✅ Create app/routing/intent_classifier.py
- classify_intent(user_query) -> {
    "intent": "refund|order_status|return_policy|shipping|general",
    "confidence": 0.0-1.0,
    "entities": {"order_id": "ORD001", "item": "laptop"}
  }
- Use lightweight LLM or regex patterns for cost optimization
```

#### 4.2 Specialist Agents
```
✅ Create app/agents/specialist_agents.py
- RefundSpecialistAgent: Handles refunds, returns, policy questions
- OrderStatusAgent: Handles tracking, delivery questions
- GeneralSupportAgent: Handles product info, account questions
- EscalationAgent: Handles complex cases requiring human review
```

#### 4.3 Router Agent
```
✅ Modify app/agent.py to RouterAgent pattern
- classify_intent() on first message
- Route to specialist agent
- Track routing decisions in analytics
- Fallback to GeneralSupportAgent if confidence < 0.7
```

#### 4.4 Agent Handoff
```
✅ Implement agent handoff protocol
- Specialist can escalate to human: save checkpoint → admin approval flow
- Context transfer: pass conversation history + entities to next agent
- Track handoffs in analytics
```

---

## **Phase 5: Policy Management Pipeline** (Automated policy updates)

### **P1 Tasks** (High priority - 4-5 hours)

#### 5.1 Policy Versioning
```
✅ Modify app/models/return_policy.py
- Add fields: version, effective_from, effective_until, is_active
- Store policy history: All versions kept for audit
```

#### 5.2 Policy Update Pipeline
```
✅ Create app/policies/policy_updater.py
- Endpoint: POST /admin/update-policy
- Upload CSV or JSON with new policies
- Validation: Check conflicts, effective dates
- Auto-activate on effective_from date (background job)
```

#### 5.3 Policy Change Notifications
```
✅ Add policy change tracking
- When policy changes → log in policy_audit_log table
- Notify affected users if they have pending cases
- Agent checks policy version at refund time (not cached version)
```

#### 5.4 External Policy Sync (Optional)
```
⚠️ If policies come from external system:
- Scheduled job: Poll external API every 6 hours
- Compare with current policies
- Auto-update if changed
- Alert admin on major changes
```

---

## **Phase 6: Production Hardening** (Deployment readiness)

### **P0 Tasks** (Critical - 8-10 hours)

#### 6.1 Docker Containerization
```
✅ Create Dockerfile (multi-stage)
✅ Create docker-compose.yml
- Services: api, postgres (replace SQLite), redis
- Volumes: ./uploads, ./logs
- Health checks: /health endpoint
```

#### 6.2 Database Migration (SQLite → PostgreSQL)
```
✅ Update app/database.py
- Change DATABASE_URL to Postgres
- Alembic migrations: alembic init, create initial migration
- Migration script: python migrate_sqlite_to_postgres.py
```

#### 6.3 Redis Cache Layer
```
✅ Replace in-memory cache with Redis
- Connection pooling
- Cache invalidation on policy updates
- TTL management
```

#### 6.4 Advanced Observability
```
✅ Add structured logging (loguru)
✅ OpenTelemetry tracing:
  - Instrument FastAPI
  - Trace agent loops
  - Export to Jaeger/Grafana
✅ Prometheus metrics:
  - /metrics endpoint
  - Track: request_duration, agent_iterations, tool_calls, cache_hits
```

#### 6.5 Rate Limiting & Security
```
✅ Add slowapi rate limiter:
  - 100 requests/hour per IP
  - 20 requests/minute per user
✅ Add PII redaction:
  - Detect credit card, SSN, email in logs
  - Redact before storing
✅ Add CORS middleware (production domains only)
✅ Add request ID tracking
```

#### 6.6 Error Recovery & Retry Logic
```
✅ Add exponential backoff for:
  - OpenAI API calls
  - External API calls (shipping, payment)
  - Database retries on conflict
✅ Dead letter queue for failed tasks
✅ Circuit breaker pattern for external services
```

#### 6.7 CI/CD Pipeline
```
✅ Create .github/workflows/ci.yml
- Run tests on PR
- Run eval suite
- Build Docker image
- Deploy to staging on merge to main
✅ Create .github/workflows/deploy.yml
- Deploy to production on tag
- Health check validation
- Rollback on failure
```

---

## **Phase 7: Advanced Features** (Nice-to-have)

### **P2 Tasks** (Lower priority - 10-12 hours)

#### 7.1 Voice Interface
```
⚠️ Add Whisper API for voice input
⚠️ Add TTS for voice responses
```

#### 7.2 Multi-language Support
```
⚠️ Detect language → translate → respond in user's language
```

#### 7.3 Proactive Notifications
```
⚠️ Email/SMS when:
  - Refund approved
  - Admin approval needed
  - Return shipment received
```

#### 7.4 Analytics Dashboard v2
```
⚠️ Add charts:
  - Agent routing distribution
  - Checkpoint resume times
  - Photo verification success rate
```

---

## **📊 Implementation Timeline**

| Phase | Priority | Time | Dependencies |
|-------|----------|------|--------------|
| **Phase 1** | P0 | 8-10h | None |
| **Phase 2** | P0 | 6-8h | Phase 1 |
| **Phase 3** | P0 | 5-6h | None (parallel with 1) |
| **Phase 4** | P1 | 6-8h | Phase 1 |
| **Phase 5** | P1 | 4-5h | None (parallel with 1-4) |
| **Phase 6** | P0 | 8-10h | Phases 1-5 complete |
| **Phase 7** | P2 | 10-12h | Phase 6 complete |

**Total Estimate: 47-59 hours (6-8 days full-time)**

---

## **🚀 Quick Start: Next 3 Steps**

**If you want to start NOW:**

1. **Phase 1.1-1.2** (Checkpoint system) - This unlocks everything else
2. **Phase 3.1-3.3** (LLM-as-judge eval) - Validate quality as you build
3. **Phase 6.1** (Docker) - Make it deployable early

Want me to **scaffold Phase 1.1 (Checkpoint Manager)** right now? I can create the file structure + base implementation and you fill in the logic.