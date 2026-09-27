from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from domain.career import CandidateProfile, JobPosting, FitEvaluation, SkillItem, ExperienceItem
from services.ingest import chunk_text
from services.tools import format_evidence, Evidence

def test_day1_domain_models():
    print("1. Testing Day 1 Pydantic Domain Schemas...")
    profile = CandidateProfile(
        full_name="Alex Rivera",
        target_role="Senior AI Engineer",
        seniority="senior",
        summary="AI engineer specializing in LLM agents, LangGraph, and high-throughput vector search.",
        skills=[
            SkillItem(name="Python", category="language", proficiency="expert"),
            SkillItem(name="LangGraph", category="framework", proficiency="expert"),
            SkillItem(name="Qdrant", category="database", proficiency="intermediate"),
            SkillItem(name="FastAPI", category="framework", proficiency="expert"),
        ],
        experience=[
            ExperienceItem(
                role="Lead AI Platform Engineer",
                company="Nexus AI",
                duration="2022 - Present",
                highlights=[
                    "Built multi-agent RAG workflow reducing customer inquiry resolution time by 45%",
                    "Architected semantic caching layer cutting LLM API costs by $12k/month",
                ],
                technologies=["Python", "LangGraph", "Qdrant", "PostgreSQL"],
            )
        ],
        github_username="alexrivera",
        total_years_experience=5.5,
    )
    assert profile.full_name == "Alex Rivera"
    assert len(profile.skills) == 4
    print("   CandidateProfile validated successfully.")

    job = JobPosting(
        title="Staff AI Solutions Architect",
        company="Stripe",
        must_have_skills=["Python", "LangGraph", "Distributed Systems", "Kubernetes"],
        nice_to_have_skills=["Go", "GraphQL"],
    )
    assert job.company == "Stripe"
    assert len(job.must_have_skills) == 4
    print("   JobPosting validated successfully.")

    fit = FitEvaluation(
        match_score=82,
        verdict="Strong Match",
        seniority_alignment="Aligned (Senior/Lead background fits Staff track)",
        key_strengths=["Python", "LangGraph", "Semantic Caching & RAG"],
        missing_hard_skills=["Kubernetes production deployment", "Go"],
        gap_closure_roadmap=["Containerize agent pipeline with Helm chart", "Add production k8s health probes"],
        summary="Strong foundation in Python agents and vector databases; stretch opportunity in Kubernetes orchestration.",
    )
    assert fit.match_score == 82
    print("   FitEvaluation validated successfully.")

def test_day1_career_vault_chunking():
    print("2. Testing Career Vault Document Chunking...")
    sample_cv = """# Alex Rivera - Resume
## Summary
Senior AI Platform Engineer with 5+ years building autonomous agents.

## Experience
### Nexus AI (2022 - Present)
- Built multi-agent RAG workflow using LangGraph and Qdrant.
- Deployed semantic similarity caching layer saving $12,000 monthly.

## Skills
- Languages: Python, TypeScript
- Frameworks: LangGraph, FastAPI, PyTorch
- Databases: PostgreSQL, Qdrant
"""
    chunks = chunk_text(sample_cv, doc_title="Alex_Rivera_CV.md", source_type="md")
    assert len(chunks) >= 2
    print(f"   Generated {len(chunks)} chunks from candidate CV.")

def main():
    print("=======================================================")
    print("Testing CareerOps AI Day 1: Scout, Profile & Fit Scorer")
    print("=======================================================")
    test_day1_domain_models()
    test_day1_career_vault_chunking()
    print("=======================================================")
    print("SUCCESS: ALL DAY 1 CORE TESTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    main()
