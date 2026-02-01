"""Configuration module using Pydantic Settings.

Provides typed configuration for adapters with environment variable support.

Usage:
    from agentecs.config import VectorStoreSettings, LLMSettings

    settings = VectorStoreSettings(collection_name="docs")
    llm = LLMSettings(model="gpt-4o", temperature=0.5)
"""

from agentecs.config.settings import LLMSettings, VectorStoreSettings

__all__ = [
    "VectorStoreSettings",
    "LLMSettings",
]
