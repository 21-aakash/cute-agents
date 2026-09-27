from __future__ import annotations

import os
from pydantic_settings import BaseSettings, SettingsConfigDict

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


class Settings(BaseSettings):
    # Project Identity
    project_name: str = "CareerOps AI"
    project_description: str = "Autonomous Career Due-Diligence & Deep Research Agent"

    # Load .env or .ENV (either works)
    model_config = SettingsConfigDict(env_file=(".env", ".ENV"), extra="ignore")

    database_url: str = "postgresql+psycopg://research:research@localhost:5432/research_agent"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_documents: str = "documents"
    qdrant_collection_memory: str = "memory"
    qdrant_collection_vault: str = "candidate_vault"

    # Embeddings: local (sentence-transformers), gemini, or openai
    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    bge_query_prefix: str = "Represent this sentence for searching relevant passages: "
    openai_embedding_model: str = "text-embedding-3-small"

    # LLM Provider: gemini | openai | ollama
    llm_provider: str = "gemini"
    
    # Gemini Configuration (Google GenAI via OpenAI-compatible endpoint)
    gemini_api_key: str = ""
    gemini_base_url: str = GEMINI_OPENAI_BASE_URL
    gemini_model: str = "gemini-2.0-flash"
    gemini_model_planner: str = ""
    gemini_model_worker: str = ""
    gemini_model_critic: str = ""
    gemini_model_chitchat: str = ""
    gemini_model_eval: str = ""

    # OpenAI Configuration
    openai_api_key: str = ""
    openai_base_url: str = DEFAULT_OPENAI_BASE_URL
    openai_model: str = "gpt-4o"
    openai_model_planner: str = ""
    openai_model_worker: str = ""
    openai_model_critic: str = ""
    openai_model_chitchat: str = ""
    openai_model_eval: str = ""

    # Ollama Configuration
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    top_k: int = 6
    memory_top_k: int = 3
    web_top_k: int = 5
    min_score: float = 0.30

    critic_pass_threshold: float = 3.5
    max_revisions: int = 2
    max_clarify_rounds: int = 2

    verbatim_turns: int = 4

    upload_dir: str = "uploads"

    # LangGraph checkpoint store: memory (dev) or postgres
    checkpoint_backend: str = "memory"
    checkpoint_connect_timeout: int = 5

    log_level: str = "INFO"
    openai_timeout: float = 120.0
    chat_request_timeout: float = 180.0

    def active_api_key(self) -> str:
        provider = self.llm_provider.lower()
        if provider == "gemini":
            return self.gemini_api_key or self.openai_api_key or os.environ.get("GEMINI_API_KEY", "")
        return self.openai_api_key or os.environ.get("OPENAI_API_KEY", "")

    def active_base_url(self) -> str:
        provider = self.llm_provider.lower()
        if provider == "gemini":
            return self.gemini_base_url
        return self.openai_base_url

    def model_for(self, role: str) -> str:
        """Role -> Model identifier based on the active provider."""
        provider = self.llm_provider.lower()
        if provider == "gemini":
            role_models = {
                "planner": self.gemini_model_planner or "gemini-2.0-flash",
                "worker": self.gemini_model_worker or "gemini-2.0-flash",
                "critic": self.gemini_model_critic or "gemini-2.0-flash",
                "chitchat": self.gemini_model_chitchat or "gemini-2.0-flash",
                "eval": self.gemini_model_eval or "gemini-2.0-flash",
                "default": self.gemini_model,
            }
            return role_models.get(role, self.gemini_model)

        if provider == "openai":
            role_models = {
                "planner": self.openai_model_planner or "gpt-4o",
                "worker": self.openai_model_worker or "gpt-4o-mini",
                "critic": self.openai_model_critic or "gpt-4o",
                "chitchat": self.openai_model_chitchat or "gpt-4o-mini",
                "eval": self.openai_model_eval or "gpt-4o-mini",
                "default": self.openai_model,
            }
            return role_models.get(role, self.openai_model)

        return self.ollama_model


settings = Settings()
