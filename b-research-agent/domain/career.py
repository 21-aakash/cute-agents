from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

SeniorityLevel = Literal["intern", "junior", "mid", "senior", "lead", "staff", "principal", "executive", "unknown"]
SkillCategory = Literal["language", "framework", "database", "cloud_infra", "ai_ml", "system_design", "soft_skill", "other"]
SkillImportance = Literal["must_have", "nice_to_have"]


class SkillItem(BaseModel):
    name: str
    category: SkillCategory = "other"
    years_experience: float | None = None
    proficiency: Literal["beginner", "intermediate", "expert"] = "intermediate"


class ExperienceItem(BaseModel):
    role: str
    company: str
    duration: str = ""
    location: str = ""
    highlights: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    metrics: str = ""
    github_link: str | None = None


class CandidateProfile(BaseModel):
    full_name: str = "Candidate"
    target_role: str = ""
    seniority: SeniorityLevel = "mid"
    summary: str = ""
    skills: list[SkillItem] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    github_username: str | None = None
    linkedin_url: str | None = None
    total_years_experience: float = 0.0


class JobPosting(BaseModel):
    title: str
    company: str = "Target Company"
    location: str = "Remote / Flexible"
    seniority_required: SeniorityLevel = "mid"
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    key_responsibilities: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    summary: str = ""
    raw_text: str = ""


class SkillMatch(BaseModel):
    skill_name: str
    category: SkillCategory = "other"
    importance: SkillImportance = "must_have"
    matched: bool = False
    evidence_quote: str = ""


class FitEvaluation(BaseModel):
    match_score: int = Field(default=0, ge=0, le=100, description="Overall match score from 0 to 100")
    verdict: Literal["Strong Match", "Moderate Match", "Reach / Stretch Role", "Low Match"] = "Moderate Match"
    seniority_alignment: str = ""
    key_strengths: list[str] = Field(default_factory=list)
    missing_hard_skills: list[str] = Field(default_factory=list)
    missing_soft_skills: list[str] = Field(default_factory=list)
    skill_matches: list[SkillMatch] = Field(default_factory=list)
    gap_closure_roadmap: list[str] = Field(default_factory=list)
    summary: str = ""
