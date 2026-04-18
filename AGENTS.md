# Pydontology Agent Guide

This guide provides essential information for AI agents working on the Pydontology project, including build/lint/test commands and code style guidelines.

## Project Overview

Pydontology is a Python package that bridges Pydantic models with semantic web technologies, generating RDF, RDFS, OWL, and SHACL artifacts from Pydantic class definitions. The core components include:

1. **Entity System**: Base classes Entity and Relation, plus JSONLDGraph
2. **Annotation Systems**: RDFS and SHACL annotations
3. **Validation Layer**: Functions for data integrity validation

## Development Environment

### Requirements

- Python 3.8+
- Dependencies: pydantic>=2.12
- Optional test dependencies: pytest, rdflib, pyshacl
- Optional example dependencies: marimo, rdflib, pyshacl

### Setup

```bash
# Install the package in development mode
pip install -e .

# Install test dependencies
pip install pytest rdflib pyshacl

# Install example dependencies
pip install marimo rdflib pyshacl
```

## Build, Test, and Lint Commands

### Build Commands

```bash
# Build the package
python -m build

# Install in development mode
pip install -e .
```

### Test Commands

```bash
# Run all tests
python -m pytest

# Run a specific test file
python -m pytest tests/test_onto.py

# Run a specific test function
python -m pytest tests/test_onto.py::test_ontology_classes_present

# Run tests with verbose output
python -m pytest -v

# Run tests with coverage report
python -m pytest --cov=pydontology
```

### Documentation Commands

```bash
# Install MkDocs and dependencies
pip install mkdocs mkdocstrings[python] mkdocs-darkly-theme "griffe-pydantic>=0.1.0"

# Build documentation
mkdocs build

# Serve documentation locally
mkdocs serve
```

## Code Style Guidelines

### Import Style

```python
# Standard library imports first
import os
import sys
from typing import Annotated, Dict, List, Optional, Union

# Third-party imports next, alphabetically ordered
import pytest
from pydantic import BaseModel, Field
from rdflib import Graph, Namespace, RDF, RDFS, OWL

# Local imports last
from pydontology.pydontology import Entity, Relation, JSONLDGraph
from pydontology.rdfs import RDFSAnnotation
from pydontology.shacl import SHACLAnnotation
```

### Type Annotations

- Always use type annotations for function parameters and return values.
- Use the `typing` module for complex types.
- Use `Optional[Type]` for parameters that can be None.
- Use `Annotated` for fields with metadata, especially RDFS and SHACL annotations.

```python
from typing import Optional, List, Dict, Annotated

def function_name(param1: str, param2: Optional[int] = None) -> Dict[str, List[str]]:
    # function body
```

### Naming Conventions

- **Classes**: Use UpperCamelCase
- **Functions/Methods**: Use snake_case
- **Variables**: Use snake_case
- **Constants**: Use UPPER_SNAKE_CASE
- **Private Methods/Variables**: Prefix with underscore (_)

### Docstrings

Use Google-style docstrings as configured in the mkdocs.yml file:

```python
def function_name(param1: str, param2: Optional[int] = None) -> Dict[str, List[str]]:
    """Short description of the function.
    
    Longer description explaining functionality in more detail.
    
    Args:
        param1: Description of the first parameter.
        param2: Description of the second parameter. Default is None.
    
    Returns:
        Description of the return value.
        
    Raises:
        ValueError: When parameter values are invalid.
    
    Examples:
        >>> function_name("example", 42)
        {'key': ['value']}
    """
```

### Error Handling

- Use specific exception types over generic ones.
- Include informative error messages.
- Validate inputs early in functions.

```python
def validate_entity(entity_id: str) -> None:
    if not entity_id:
        raise ValueError("Entity ID cannot be empty")
    if not entity_id.startswith("urn:"):
        raise ValueError(f"Entity ID must start with 'urn:' but got '{entity_id}'")
```

### Testing Guidelines

- Follow the test-driven development approach.
- Write tests for all new features.
- Group related tests within the same test file.
- Use descriptive test names that explain what the test verifies.
- Use fixtures for common test setup.
- Make test assertions specific and precise.

```python
def test_entity_validation_rejects_empty_id():
    """Test that entity validation rejects empty ID."""
    with pytest.raises(ValueError) as exc:
        validate_entity("")
    assert "cannot be empty" in str(exc.value)
```

### CI/CD Workflow

The project uses GitHub Actions for:
- AI implementation of issues
- AI code review
- AI chat for assistance

AI implementation workflow:
1. Tests are designed first based on issue description
2. Implementation is created to pass tests
3. Changes are committed and pushed to a branch
4. Optional PR creation for review

## Project Structure

```
pydontology/
├── pydontology/
│   ├── __init__.py       # Package initialization
│   ├── pydontology.py    # Core implementation
│   ├── rdfs.py           # RDF Schema annotation
│   ├── shacl.py          # SHACL annotation
│   └── validators.py     # Validation functions
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── test_onto.py      # Ontology tests
│   └── test_shacl.py     # SHACL validation tests
├── agents/               # AI agent prompt files
├── docs/                 # Generated documentation
└── mkdocs/               # Documentation source
```

## Implementation Patterns

### Entity Definition

```python
class Person(Entity):
    """Person entity class with documentation."""
    
    name: Annotated[
        str, 
        SHACLAnnotation.minLength(1),
        SHACLAnnotation.maxLength(100)
    ] = Field(description="Person's name")
    
    age: Annotated[
        Optional[int],
        SHACLAnnotation.minInclusive(0),
        SHACLAnnotation.maxInclusive(150)
    ] = Field(default=None, description="Person's age in years")
```

### Relation Definition

```python
manager: Annotated[
    Optional[Relation],
    RDFSAnnotation.range("Manager"),
    SHACLAnnotation.shclass("Manager"),
    SHACLAnnotation.maxCount(1)
] = Field(default=None, description="Link to manager")
```

### Ontology Creation

```python
onto = Pydontology(ontology=Person | Employee | Manager | Department)
graph = onto.ontology_graph()
```

## Pull Request Guidelines

When submitting code changes:

1. Ensure all tests pass
2. Add new tests for any new functionality
3. Follow the existing code style
4. Update documentation if necessary
5. Keep changes focused on a single issue
