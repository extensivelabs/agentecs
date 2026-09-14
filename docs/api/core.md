# Core API

Stateless, SOLID building blocks for the ECS framework.

## Overview

The core API provides the fundamental abstractions for entities, components, systems, and queries. These are pure, stateless functionalities that can be composed to build complex agent behaviors.

**Key Principles:**
- **Protocols over inheritance**: Use runtime-checkable protocols for flexibility
- **Functional core**: All operations are deterministic and stateless
- **Composability**: Mix and match protocols to create rich component behaviors

---

## Component Module

Define components with optional operation protocols.

### Component Decorator

::: agentecs.api.decorators.component
    options:
      show_root_heading: true
      show_source: true
      members:
        - component

### Component Registry

::: agentecs.services.registry.ComponentRegistry
    options:
      show_root_heading: true
      show_source: true

::: agentecs.services.registry.get_registry
    options:
      show_root_heading: true
      show_source: true

### Operation Protocols

Components can optionally implement these protocols to enable advanced operations:

::: agentecs.models.component.Combinable
    options:
      show_root_heading: true
      show_source: true

::: agentecs.models.component.Splittable
    options:
      show_root_heading: true
      show_source: true

### Utility Functions

::: agentecs.functions.component.combine_protocol_or_fallback
    options:
      show_root_heading: true
      show_source: true

::: agentecs.functions.component.split_protocol_or_fallback
    options:
      show_root_heading: true
      show_source: true

::: agentecs.functions.component.reduce_components
    options:
      show_root_heading: true
      show_source: true

---

## Identity Module

Entity identification with generational indices.

::: agentecs.models.identity.EntityId
    options:
      show_root_heading: true
      show_source: true

::: agentecs.models.identity.SystemEntity
    options:
      show_root_heading: true
      show_source: true

---

## Query Module

Query builder for filtering entities by component types.

::: agentecs.models.query.Query
    options:
      show_root_heading: true
      show_source: true

::: agentecs.models.query.AccessPattern
    options:
      show_root_heading: true
      show_source: true

---

## System Module

Define systems with declared access patterns.

### System Decorator

::: agentecs.api.decorators.system
    options:
      show_root_heading: true
      show_source: true

### System Metadata

::: agentecs.models.system.SystemDescriptor
    options:
      show_root_heading: true
      show_source: true

::: agentecs.models.system.SystemMode
    options:
      show_root_heading: true
      show_source: true
