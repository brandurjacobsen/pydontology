# Pydontology Architecture

## Overview

Pydontology is a Python library that enables the creation of ontologies using Pydantic models. It bridges the gap between Python data modeling and semantic web technologies by automatically generating RDF ontologies and SHACL validation schemas from Pydantic class definitions.

## Core Components

### 1. Entity System (`pydontology/pydontology.py`)

The foundation of Pydontology is built around several key classes:

- **`Entity`**: The base class for all ontology entities. Inherits from Pydantic's `BaseModel` and provides the core functionality for semantic modeling.
- **`Relation`**: Represents relationships between entities in the ontology.
- **`JSONLDGraph`**: Encapsulates JSON-LD documents and provides methods for generating ontology and SHACL graphs.

### 2. Annotation Systems

#### RDFS Annotations (`pydontology/rdfs.py`)
- **`RDFSAnnotation`**: Provides methods for setting RDFS (RDF Schema) annotations
- Supports domain and range specifications for properties
- Enables semantic relationships between classes and properties

#### SHACL Annotations (`pydontology/shacl.py`)
- **`SHACLAnnotation`**: Provides methods for setting SHACL (Shapes Constraint Language) annotations
- Supports various constraint types:
  - Data type constraints
  - Cardinality constraints (min/max count)
  - String constraints (pattern, length)
  - Numeric constraints (min/max inclusive/exclusive)
  - Node kind and class constraints

### 3. Validation Layer (`pydontology/validators.py`)

Contains validation functions for ensuring data integrity:
- Whitespace validation
- Node kind validation
- Data type validation
- Numeric range validation
- Regular expression pattern validation

## Architecture Flow

```
Pydantic Models with Annotations
           ↓
    Entity Base Classes
           ↓
    make_model() Function
           ↓
    JSONLDGraph Generation
           ↓
┌─────────────────┬─────────────────┐
│  Ontology Graph │   SHACL Graph   │
│   (RDFS/OWL)    │  (Validation)   │
└─────────────────┴─────────────────┘
```

## Key Design Patterns

### 1. Model Generation Pattern

The `make_model()` function serves as the main entry point, taking an Entity class hierarchy and generating a complete model with both ontology and SHACL validation capabilities.

### 2. Graph Generation Pattern

The `JSONLDGraph` class uses class methods to generate different types of graphs:
- `ontology_graph()`: Generates RDF ontology definitions
- `shacl_graph()`: Generates SHACL validation schemas

### 3. Annotation Pattern

Annotations are implemented as static methods that return dataclass instances, providing type safety and validation for semantic metadata.

## Data Flow

1. **Model Definition**: Users define Python classes inheriting from `Entity`
2. **Annotation**: Classes and fields are annotated with RDFS and SHACL metadata
3. **Model Creation**: `make_model()` processes the class hierarchy
4. **Graph Generation**: The system generates JSON-LD graphs for ontology and validation
5. **Export**: Graphs can be serialized and used with standard semantic web tools

## Module Dependencies

- **Core**: Built on Pydantic for data validation and modeling
- **Semantic Web**: Generates standard RDF/RDFS/OWL and SHACL outputs
- **JSON-LD**: Uses JSON-LD format for interoperability
- **Testing**: Comprehensive test suite using pytest and rdflib for validation

## Extension Points

The architecture supports extension through:
- Custom Entity subclasses
- Additional annotation types
- Custom validation functions
- Plugin-based graph generators

## Benefits

1. **Type Safety**: Leverages Python's type system and Pydantic validation
2. **Standards Compliance**: Generates standard semantic web formats
3. **Developer Experience**: Familiar Python syntax for ontology development
4. **Validation**: Built-in SHACL constraint generation
5. **Interoperability**: JSON-LD output works with existing semantic web tools
