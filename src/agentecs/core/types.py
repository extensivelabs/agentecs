"""Core type definitions for AgentECS."""

type Copy[T] = T
"""Type alias indicating a value is a copy that won't auto-persist.

When you see `Copy[T]` in a return type, the returned value is a deep copy.
Mutations to this copy do NOT affect world state. To persist changes,
explicitly write back via `world[entity, Type] = component` or `access.update()`.
"""
