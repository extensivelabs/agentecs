"""Configuration settings using Pydantic Settings.

Provides typed configuration with environment variable support for adapters.

Usage:
    from agentecs.config import VectorStoreSettings, LLMSettings

    # Load from environment variables (VECTORSTORE_*, LLM_*)
    vs_settings = VectorStoreSettings()
    llm_settings = LLMSettings()

    # Or override with explicit values
    vs_settings = VectorStoreSettings(collection_name="my_docs")
"""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError as e:
    raise ImportError(
        "pydantic-settings is required for config module. "
        "Install with: pip install agentecs[config]"
    ) from e


class VectorStoreSettings(BaseSettings):  # type: ignore[misc]
    """Configuration for vector store adapters.

    Attributes:
        collection_name: Name of the collection/index.
        persist_directory: Path for persistent storage (None for ephemeral).
        distance_metric: Distance function for similarity (cosine, l2, ip).

    Environment Variables:
        VECTORSTORE_COLLECTION_NAME
        VECTORSTORE_PERSIST_DIRECTORY
        VECTORSTORE_DISTANCE_METRIC
    """

    model_config = SettingsConfigDict(
        env_prefix="VECTORSTORE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    collection_name: str = "default"
    persist_directory: str | None = None
    distance_metric: str = "cosine"


class LLMSettings(BaseSettings):  # type: ignore[misc]
    """Configuration for LLM adapters.

    Attributes:
        model: Model name/identifier.
        temperature: Sampling temperature (0.0-2.0).
        max_tokens: Maximum tokens in response.
        api_key: API key (prefer environment variable).
        base_url: Custom API base URL (for proxies/local models).
        timeout: Request timeout in seconds.
        max_retries: Number of retries on failure.

    Environment Variables:
        LLM_MODEL
        LLM_TEMPERATURE
        LLM_MAX_TOKENS
        LLM_API_KEY (or OPENAI_API_KEY as fallback)
        LLM_BASE_URL
        LLM_TIMEOUT
        LLM_MAX_RETRIES
    """

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int | None = None
    api_key: str | None = None
    base_url: str | None = None
    timeout: float = 60.0
    max_retries: int = 3
