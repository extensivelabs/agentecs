# Adapters API

Optional adapters for external integrations.

## Overview

AgentECS provides protocol-based adapters for common external services:
- **Vector Stores**: Semantic search and RAG (ChromaDB)
- **LLM Clients**: Structured output with multiple providers (Instructor)
- **Configuration**: Type-safe settings with environment variables

**Design Principles:**
- Optional dependencies: Don't require installation unless used
- Protocol-based: Easy to implement custom adapters
- Multi-provider: Support multiple backends per protocol
- Type-safe: Generics ensure type safety throughout

---

## Vector Store Adapter

Semantic search and retrieval-augmented generation.

### VectorStore Protocol

::: agentecs.protocols.vectorstore.VectorStore
    options:
      show_root_heading: true
      show_source: true
      members:
        - add
        - add_batch
        - get
        - get_batch
        - update
        - delete
        - delete_batch
        - search
        - count

### ChromaDB Adapter

::: agentecs.adapters.chroma.ChromaAdapter
    options:
      show_root_heading: true
      show_source: true
      members:
        - from_memory
        - from_disk
        - add
        - add_batch
        - get
        - search

### Models

::: agentecs.models.vectorstore.SearchMode
    options:
      show_root_heading: true
      show_source: true

::: agentecs.models.vectorstore.SearchResult
    options:
      show_root_heading: true
      show_source: true

::: agentecs.models.vectorstore.VectorStoreItem
    options:
      show_root_heading: true
      show_source: true

::: agentecs.models.vectorstore.Filter
    options:
      show_root_heading: true
      show_source: true

::: agentecs.models.vectorstore.FilterGroup
    options:
      show_root_heading: true
      show_source: true

---

## LLM Client Adapter

Structured LLM output with multiple providers.

### LLMClient Protocol

::: agentecs.protocols.llm.LLMClient
    options:
      show_root_heading: true
      show_source: true
      members:
        - call
        - call_async
        - stream
        - stream_async

### Instructor Adapter

::: agentecs.adapters.instructor.InstructorAdapter
    options:
      show_root_heading: true
      show_source: true
      members:
        - from_openai_client
        - from_anthropic
        - from_litellm
        - from_gemini
        - call
        - call_async
        - stream
        - stream_async

### Models

::: agentecs.models.llm.Message
    options:
      show_root_heading: true
      show_source: true
      members:
        - system
        - user
        - assistant

::: agentecs.models.llm.MessageRole
    options:
      show_root_heading: true
      show_source: true

---

## Configuration

Type-safe configuration with Pydantic Settings.

::: agentecs.models.settings.VectorStoreSettings
    options:
      show_root_heading: true
      show_source: true

::: agentecs.models.settings.LLMSettings
    options:
      show_root_heading: true
      show_source: true

---

## Installation

Install adapter dependencies:

```bash
# Vector store adapter
pip install agentecs[vector]

# LLM adapter
pip install agentecs[llm]

# Configuration
pip install agentecs[config]

# All adapters
pip install agentecs[all]
```

---

## Usage Examples

### Vector Store

```python
from pydantic import BaseModel
from agentecs.adapters.chroma import ChromaAdapter
from agentecs.models.vectorstore import SearchMode

class Document(BaseModel):
    title: str
    content: str

# Create adapter
store = ChromaAdapter.from_memory("docs", Document)

# Add documents
store.add("doc1", embedding=[...], text="content", data=Document(...))

# Search
results = store.search(
    query_embedding=[...],
    mode=SearchMode.HYBRID,
    limit=10
)
```

### LLM Client

```python
from pydantic import BaseModel
from agentecs.adapters.instructor import InstructorAdapter
from agentecs.models.llm import Message
from agentecs.models.settings import LLMSettings

class Analysis(BaseModel):
    sentiment: str
    confidence: float

# Create adapter
adapter = InstructorAdapter.from_litellm(
    settings=LLMSettings(model="anthropic/claude-3-5-sonnet-20241022")
)

# Call with structured output
messages = [Message.user("Analyze: Great product!")]
result = adapter.call(messages, response_model=Analysis)
```
