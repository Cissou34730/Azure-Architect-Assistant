---
description: 'Python coding conventions and guidelines'
applyTo: '**/*.py'
---

Apply the [general coding guidelines](./general-coding.instructions.md) to all code.

# Python Coding Conventions

## Core Principles

- Write clear, maintainable, and idiomatic Python code.
- Always include type hints using modern built-in generics (`list[str]`, `dict[str, int]`, etc.).
- Use docstrings following **PEP 257** conventions.
- Follow **PEP 8** for formatting and naming.

---

# 1. Python-Specific Instructions

## Docstrings & Comments
- Every public function, class, and module MUST include a docstring.
- Docstrings must follow PEP 257 structure:
  - Summary line
  - Optional detailed description
  - `Args:` or `Parameters:` section
  - `Returns:` section
  - `Raises:` when relevant
- Use comments only when they clarify *intent*, not restate obvious logic.

## Type Hints
- Use Python 3.10+ built-in generics:
  - `list[str]`, `dict[str, float]`, `tuple[int, ...]`, etc.
- Avoid `Any` unless strictly necessary.
- Use `typing.Optional[...]` or `| None` depending on readability.

## Function & Module Structure
- Keep functions short and focused.
- For complex logic, break down the behavior into smaller units.
- Avoid modules that mix unrelated responsibilities.
- As a guideline, try to keep modules reasonably sized (e.g., < 300 lines), unless the structure naturally stays cohesive.

## Imports
- Prefer module-level imports at the top of the file.
- Use imports inside functions only when:
  - needed to avoid circular imports
  - the dependency is optional
  - the import is heavy and should not slow module import time
  - the logic is rarely executed

---

# 2. General Code Quality Instructions

- Prioritize clarity over cleverness.
- For algorithmic code, briefly document the approach in the docstring.
- Document non-obvious design decisions.
- Handle edge cases explicitly and document expected behavior.
- Use consistent naming following Python conventions:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `SCREAMING_SNAKE_CASE` for constants
- Avoid side effects at module import time where possible.

---

# 3. Code Style & Formatting

- Follow **PEP 8** formatting conventions.
- Use 4 spaces for indentation.
- Keep line length around 79–88 characters (project-default or Black default).
- Use blank lines to separate classes, functions, and logical blocks.
- Place imports in this order:
  1. Standard library
  2. Third-party libraries
  3. Local modules  
  (following PEP 8 import grouping)

---

# 4. Testing Guidelines (pytest)

We use **pytest** as the lightweight testing framework.

## Test Structure
- Test files must follow naming conventions:
  - `test_*.py` or `*_test.py`
- Place tests either:
  - alongside the module (`module_name/test_module_name.py`), or
  - under a dedicated `tests/` folder, depending on project layout.

## Test Requirements
- All critical functions must have at least one test.
- Include edge cases:
  - empty input
  - invalid types
  - large datasets
  - boundary values
- Use clear and descriptive test names.
- Prefer simple assertions (`assert <expr>`) using pytest’s style.

## Mocking & Isolation
- Use `unittest.mock` or `pytest-mock` if mocking is required.
- Avoid dependencies on external services in tests.
- Keep tests small and isolated.

---

# 5. Example of Proper Documentation

```python
import math

def calculate_area(radius: float) -> float:
    """
    Calculate the area of a circle.

    Parameters:
        radius: Non-negative radius of the circle.

    Returns:
        The area in square units (π * r^2).

    Raises:
        ValueError: If radius is negative.
    """
    if radius < 0:
        raise ValueError("radius must be non-negative")
    return math.pi * radius ** 2
