# Feature: Reverse Ontology → Pydontology

Convert an existing RDF/OWL ontology (Turtle format) into Pydontology `Entity` classes.

## Motivation

Pydontology currently works in one direction: define Python `Entity` subclasses with typed fields and annotations, then generate JSON-LD ontology graphs, SHACL shapes, and JSON schemas. This feature adds the reverse path — ingest a Turtle ontology and produce Pydontology-compatible Python source code.

## Scope (v1)

- Parse Turtle files via `rdflib`
- Extract classes (`rdfs:Class` / `owl:Class`) and properties (`owl:ObjectProperty` / `owl:DatatypeProperty`)
- Generate Python `Entity` subclasses with proper field types, annotations, and docstrings
- Handle subclass hierarchies, property domains/ranges, OWL property characteristics
- Detect `LangStr` fields from language-tagged literals in the graph
- Skip `owl:AnnotationProperty`

### Out of Scope (v1)

- SHACL shapes (`sh:NodeShape`, `sh:PropertyShape`, constraints)
- OWL restrictions (`owl:Restriction`, `owl:someValuesFrom`, etc.)
- `owl:intersectionOf`
- Instance data generation (the reverse of `jsonld_graph`)

## Module

New module: `pydontology/reverse.py`

## API

```python
def turtle_to_pydontology(
    turtle_source: str | Path,
    output_path: str | Path | None = None,
) -> str:
    """Parse a Turtle ontology and generate Pydontology Entity class source.

    Args:
        turtle_source: Path to a .ttl file, or a Turtle string.
        output_path: If given, write the generated Python source to this file.

    Returns:
        The generated Python source code as a string.
    """
```

## Pipeline

### Step 1 — Parse

Use `rdflib.Graph().parse(turtle_source, format="turtle")`. The graph carries namespace bindings for compact IRI resolution.

### Step 2 — Extract Classes

SPARQL query for all nodes typed `rdfs:Class` or `owl:Class`. For each class node:

| Turtle construct | Python output |
|---|---|
| IRI → name | Compact IRI local name via `graph.namespace_manager.compute_qname(iri)` |
| `rdfs:label` | `RDFSAnnotation.label(...)` (or class docstring) |
| `rdfs:comment` | Class docstring |
| `rdfs:subClassOf` (first) | Python parent class |
| `rdfs:subClassOf` (additional) | `RDFSAnnotation.subClassOf(...)` |
| `owl:equivalentClass` | `OWLAnnotation.equivalentClass(...)` |
| `rdfs:seeAlso` | `RDFSAnnotation.seeAlso(...)` |
| `rdfs:isDefinedBy` | `RDFSAnnotation.isDefinedBy(...)` |

### Step 3 — Extract Properties

SPARQL query for all nodes typed `owl:ObjectProperty`, `owl:DatatypeProperty`, or any OWL property characteristic (`owl:TransitiveProperty`, etc.). For each property node:

| Turtle construct | Python output |
|---|---|
| IRI → name | Compact IRI local name (same method as classes) |
| `rdf:type owl:ObjectProperty` | Field type: `Relation` |
| `rdf:type owl:DatatypeProperty` | Field type: Python type from `rdfs:range` XSD mapping (or `str` default) |
| `rdfs:domain` | Class ownership (duplicated on each domain class) |
| `rdfs:range` (object prop) | `Relation(id=full_iri)` |
| `rdfs:range` (data prop) | XSD → Python type via reverse `TYPE_MAP` |
| Language-tagged literals detected | Field type: `LangStr` |
| `rdfs:label` | `RDFSAnnotation.label(...)` |
| `rdfs:comment` | `RDFSAnnotation.comment(...)` (or field `description=`) |
| `rdfs:subPropertyOf` | `RDFSAnnotation.subPropertyOf(...)` |
| `owl:inverseOf` | `OWLAnnotation.inverseOf(...)` |
| `owl:equivalentProperty` | `OWLAnnotation.equivalentProperty(...)` |
| `owl:TransitiveProperty` | `OWLAnnotation.transitiveProperty(True)` |
| `owl:SymmetricProperty` | `OWLAnnotation.symmetricProperty(True)` |
| `owl:FunctionalProperty` | `OWLAnnotation.functionalProperty(True)` |
| `owl:InverseFunctionalProperty` | `OWLAnnotation.inverseFunctionalProperty(True)` |
| `owl:AnnotationProperty` | **Skipped** |

### Step 4 — Assign Properties to Classes

For each property:
- **One `rdfs:domain`**: field goes on that class.
- **Multiple `rdfs:domain`**: field duplicated on each domain class. Pydontology's duplicate property handling merges definitions at runtime.
- **No `rdfs:domain`**: skip and emit a warning.
- **Domain is `owl:Thing`**: skip and emit a warning (duplicating on every class would be messy).
- **No parent class**: defaults to `Entity` base.

All fields are `Optional[...] = None` since Turtle schemas lack cardinality without SHACL shapes.

### Step 5 — Generate Python Source

1. Topological sort classes so parents appear before children.
2. Emit imports (`Entity`, `Relation`, `LangStr`, `Optional`, `Annotated`, `RDFSAnnotation`, `OWLAnnotation`).
3. Emit a header comment listing the source file and detected namespaces.
4. Emit classes with proper field definitions and annotations.

## Design Decisions

| Decision | Choice |
|---|---|
| Output format | Python source file (`.py`) |
| Class naming | Compact IRI local name via `rdflib` namespace manager |
| Property/field naming | Compact IRI local name (same method) |
| Namespace handling | Keep full IRIs in `Relation(id=...)` annotations |
| Multiple `rdfs:subClassOf` | First as Python parent, rest as `RDFSAnnotation.subClassOf(...)` |
| Orphan properties (no domain) | Skip and warn |
| Properties on multiple domains | Duplicate field on each domain class |
| Datatype property with no `rdfs:range` | Default to `str` |
| LangStr detection | Check for language-tagged literals (`"value"@en`) in the graph |
| Annotation properties | Skipped |
| Integration point | New module `pydontology/reverse.py` |

## Edge Cases

- **Name collisions**: field name matches `id` or another reserved name → suffix with `_prop`.
- **Unrecognized XSD types**: default to `str` with a warning.
- **Properties on `owl:Thing`**: skip with warning.
- **No explicit parent class**: default to `Entity`.

## Example

### Input (Turtle)

```turtle
@prefix ex: <http://example.org/ns#> .

ex:Person a rdfs:Class ;
    rdfs:label "Person" ;
    rdfs:comment "A human being" ;
    rdfs:subClassOf ex:Agent .

ex:name a owl:DatatypeProperty ;
    rdfs:domain ex:Person ;
    rdfs:range xsd:string ;
    rdfs:label "name" .

ex:knows a owl:ObjectProperty ;
    rdfs:domain ex:Person ;
    rdfs:range ex:Person ;
    rdfs:label "knows" .
```

### Output (Python)

```python
from typing import Annotated, Optional

from pydontology import Entity, LangStr, Relation
from pydontology.owl import OWLAnnotation
from pydontology.rdfs import RDFSAnnotation

class Agent(Entity):
    pass

class Person(Agent):
    """A human being"""

    name: Annotated[
        Optional[str],
        RDFSAnnotation.label("name"),
    ] = None

    knows: Annotated[
        Optional[Relation],
        RDFSAnnotation.label("knows"),
    ] = None
```

## Future Extensions (v2+)

- SHACL shape parsing and generation (`sh:NodeShape`, `sh:PropertyShape`, all constraint components)
- OWL restriction support
- `owl:intersectionOf` support
- Instance data generation from RDF data graphs
- Support for additional RDF serialization formats (RDF/XML, JSON-LD, N-Triples)