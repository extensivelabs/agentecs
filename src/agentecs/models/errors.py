"""Exceptions raised across the runtime."""

from __future__ import annotations


class AccessViolationError(Exception):
    """Raised when system accesses undeclared components."""

    pass


class ConflictError(Exception):
    """Raised when parallel systems write the same component on same entity."""

    pass
