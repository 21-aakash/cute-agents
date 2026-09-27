"""
Analytics tracking for agent performance monitoring.

Tracks:
- Tool call frequency and success rate
- Agent completion rate and latency
- Guardrail interventions
- Session statistics
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import json
import logging

from learning.code_manual.Refundbot.app.session import get_db, SessionModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# In-memory analytics (production would use Redis/TimeSeries DB)
class AnalyticsStore:
    def __init__(self):
        self.tool_calls: List[Dict] = []
        self.agent_runs: List[Dict] = []
        self.guardrail_blocks: List[Dict] = []
        # P0 Metrics
        self.conversation_outcomes: List[Dict] = []  # resolved, escalated, abandoned
        self.user_feedback: List[Dict] = []  # thumbs up/down (CSAT)
        self.token_usage: List[Dict] = []  # OpenAI token consumption
        # P1 Metrics
        self.refund_decisions: List[Dict] = []  # auto_approved, escalated
        self.conversation_lengths: List[Dict] = []  # message count per session
    
    def record_tool_call(self, tool_name: str, success: bool, latency_ms: float):
        """Record a tool execution."""
        self.tool_calls.append({
            "timestamp": datetime.utcnow().isoformat(),
            "tool": tool_name,
            "success": success,
            "latency_ms": latency_ms
        })
        # Keep last 1000 records
        if len(self.tool_calls) > 1000:
            self.tool_calls = self.tool_calls[-1000:]
    
    def record_agent_run(self, session_id: str, iterations: int, success: bool, latency_ms: float):
        """Record an agent execution."""
        self.agent_runs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "iterations": iterations,
            "success": success,
            "latency_ms": latency_ms
        })
        if len(self.agent_runs) > 1000:
            self.agent_runs = self.agent_runs[-1000:]
    
    def record_guardrail_block(self, block_type: str, reason: str):
        """Record a guardrail intervention."""
        self.guardrail_blocks.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": block_type,
            "reason": reason
        })
        if len(self.guardrail_blocks) > 1000:
            self.guardrail_blocks = self.guardrail_blocks[-1000:]
    
    # P0 Metrics
    def record_conversation_outcome(self, session_id: str, outcome: str, message_count: int):
        """Record conversation outcome: resolved, escalated, or abandoned."""
        self.conversation_outcomes.append({
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "outcome": outcome,  # resolved, escalated, abandoned
            "message_count": message_count
        })
        if len(self.conversation_outcomes) > 1000:
            self.conversation_outcomes = self.conversation_outcomes[-1000:]
    
    def record_user_feedback(self, session_id: str, rating: str):
        """Record CSAT feedback: positive or negative."""
        self.user_feedback.append({
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "rating": rating  # positive, negative
        })
        if len(self.user_feedback) > 1000:
            self.user_feedback = self.user_feedback[-1000:]
    
    def record_token_usage(self, session_id: str, prompt_tokens: int, completion_tokens: int, cost: float):
        """Record OpenAI token consumption and cost."""
        self.token_usage.append({
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost": cost
        })
        if len(self.token_usage) > 1000:
            self.token_usage = self.token_usage[-1000:]
    
    # P1 Metrics
    def record_refund_decision(self, order_id: str, decision: str, amount: float):
        """Record refund decision: auto_approved or escalated."""
        self.refund_decisions.append({
            "timestamp": datetime.utcnow().isoformat(),
            "order_id": order_id,
            "decision": decision,  # auto_approved, escalated
            "amount": amount
        })
        if len(self.refund_decisions) > 1000:
            self.refund_decisions = self.refund_decisions[-1000:]


# Global analytics store
analytics = AnalyticsStore()


async def get_analytics_summary() -> Dict:
    """
    Get comprehensive analytics summary.
    
    Returns:
        Analytics summary with tool stats, agent performance, sessions
    """
    # Tool call statistics
    tool_stats = defaultdict(lambda: {"total": 0, "success": 0, "avg_latency": 0.0})
    for call in analytics.tool_calls:
        tool_stats[call["tool"]]["total"] += 1
        if call["success"]:
            tool_stats[call["tool"]]["success"] += 1
        tool_stats[call["tool"]]["avg_latency"] += call["latency_ms"]
    
    # Calculate success rates and avg latency
    for tool, stats in tool_stats.items():
        if stats["total"] > 0:
            stats["success_rate"] = round(stats["success"] / stats["total"] * 100, 1)
            stats["avg_latency"] = round(stats["avg_latency"] / stats["total"], 1)
    
    # Agent run statistics
    total_runs = len(analytics.agent_runs)
    successful_runs = sum(1 for run in analytics.agent_runs if run["success"])
    avg_iterations = round(sum(run["iterations"] for run in analytics.agent_runs) / max(total_runs, 1), 1)
    avg_latency = round(sum(run["latency_ms"] for run in analytics.agent_runs) / max(total_runs, 1), 1)
    
    # Guardrail statistics
    guardrail_stats = defaultdict(int)
    for block in analytics.guardrail_blocks:
        guardrail_stats[block["type"]] += 1
    
    # P0: Conversation Outcome Statistics
    total_outcomes = len(analytics.conversation_outcomes)
    resolved = sum(1 for o in analytics.conversation_outcomes if o["outcome"] == "resolved")
    escalated = sum(1 for o in analytics.conversation_outcomes if o["outcome"] == "escalated")
    abandoned = sum(1 for o in analytics.conversation_outcomes if o["outcome"] == "abandoned")
    
    resolution_rate = round(resolved / max(total_outcomes, 1) * 100, 1)
    escalation_rate = round(escalated / max(total_outcomes, 1) * 100, 1)
    
    # P0: CSAT (Customer Satisfaction)
    total_feedback = len(analytics.user_feedback)
    positive_feedback = sum(1 for f in analytics.user_feedback if f["rating"] == "positive")
    csat_score = round(positive_feedback / max(total_feedback, 1) * 100, 1)
    
    # P0: Cost per Conversation
    total_cost = sum(t["cost"] for t in analytics.token_usage)
    total_tokens = sum(t["total_tokens"] for t in analytics.token_usage)
    conversations_count = len(set(t["session_id"] for t in analytics.token_usage)) or 1
    cost_per_conversation = round(total_cost / conversations_count, 4)
    avg_tokens_per_conv = round(total_tokens / conversations_count, 0)
    
    # P0: Error Rate
    total_tool_calls = len(analytics.tool_calls)
    failed_calls = sum(1 for c in analytics.tool_calls if not c["success"])
    error_rate = round(failed_calls / max(total_tool_calls, 1) * 100, 1)
    
    # P1: Refund Approval Rate
    total_refunds = len(analytics.refund_decisions)
    auto_approved = sum(1 for r in analytics.refund_decisions if r["decision"] == "auto_approved")
    refund_approval_rate = round(auto_approved / max(total_refunds, 1) * 100, 1)
    
    # P1: Average Conversation Length
    avg_conv_length = round(
        sum(o["message_count"] for o in analytics.conversation_outcomes) / max(total_outcomes, 1), 1
    ) if analytics.conversation_outcomes else 0.0
    
    # Session statistics from database
    async with get_db() as db:
        # Total sessions
        total_sessions = await db.scalar(select(func.count(SessionModel.session_id)))
        
        # Active sessions (last 24h)
        yesterday = datetime.utcnow() - timedelta(days=1)
        active_24h = await db.scalar(
            select(func.count(SessionModel.session_id))
            .where(SessionModel.updated_at >= yesterday)
        )
        
        # Sessions last 7d
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_7d = await db.scalar(
            select(func.count(SessionModel.session_id))
            .where(SessionModel.updated_at >= week_ago)
        )
    
    return {
        "overview": {
            "total_agent_runs": total_runs,
            "success_rate": round(successful_runs / max(total_runs, 1) * 100, 1),
            "avg_iterations": avg_iterations,
            "avg_latency_ms": avg_latency,
            "total_tool_calls": len(analytics.tool_calls),
            "guardrail_blocks": len(analytics.guardrail_blocks)
        },
        # P0 Metrics
        "production_metrics": {
            "resolution_rate": resolution_rate,
            "escalation_rate": escalation_rate,
            "csat_score": csat_score,
            "cost_per_conversation": cost_per_conversation,
            "error_rate": error_rate,
            # P1 Metrics
            "refund_approval_rate": refund_approval_rate,
            "avg_conversation_length": avg_conv_length,
            "avg_tokens_per_conv": avg_tokens_per_conv,
            # Detailed breakdowns
            "outcomes": {
                "resolved": resolved,
                "escalated": escalated,
                "abandoned": abandoned,
                "total": total_outcomes
            },
            "feedback": {
                "positive": positive_feedback,
                "negative": total_feedback - positive_feedback,
                "total": total_feedback
            },
            "cost": {
                "total_cost": round(total_cost, 2),
                "total_tokens": total_tokens
            }
        },
        "tools": dict(tool_stats),
        "guardrails": dict(guardrail_stats),
        "sessions": {
            "total": total_sessions or 0,
            "active_24h": active_24h or 0,
            "active_7d": active_7d or 0
        },
        "recent_activity": {
            "last_10_runs": analytics.agent_runs[-10:] if analytics.agent_runs else [],
            "last_10_tool_calls": analytics.tool_calls[-10:] if analytics.tool_calls else []
        }
    }


async def get_time_series_data(hours: int = 24) -> Dict:
    """
    Get time-series data for charts.
    
    Args:
        hours: Number of hours to include
    
    Returns:
        Time-series data for visualization
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Filter recent data
    recent_runs = [
        r for r in analytics.agent_runs 
        if datetime.fromisoformat(r["timestamp"]) >= cutoff
    ]
    
    recent_tools = [
        t for t in analytics.tool_calls
        if datetime.fromisoformat(t["timestamp"]) >= cutoff
    ]
    
    # Group by hour
    hourly_data = defaultdict(lambda: {
        "runs": 0,
        "success": 0,
        "tool_calls": 0,
        "avg_latency": []
    })
    
    for run in recent_runs:
        hour = datetime.fromisoformat(run["timestamp"]).strftime("%Y-%m-%d %H:00")
        hourly_data[hour]["runs"] += 1
        if run["success"]:
            hourly_data[hour]["success"] += 1
        hourly_data[hour]["avg_latency"].append(run["latency_ms"])
    
    for tool in recent_tools:
        hour = datetime.fromisoformat(tool["timestamp"]).strftime("%Y-%m-%d %H:00")
        hourly_data[hour]["tool_calls"] += 1
    
    # Calculate averages
    for hour_data in hourly_data.values():
        if hour_data["avg_latency"]:
            hour_data["avg_latency"] = round(
                sum(hour_data["avg_latency"]) / len(hour_data["avg_latency"]), 1
            )
        else:
            hour_data["avg_latency"] = 0
    
    # Sort by time
    sorted_data = sorted(hourly_data.items())
    
    return {
        "hours": [h for h, _ in sorted_data],
        "runs": [d["runs"] for _, d in sorted_data],
        "success": [d["success"] for _, d in sorted_data],
        "tool_calls": [d["tool_calls"] for _, d in sorted_data],
        "avg_latency": [d["avg_latency"] for _, d in sorted_data]
    }
