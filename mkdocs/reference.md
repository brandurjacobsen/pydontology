# Core classes and methods
::: pydontology.pydontology.Entity
::: pydontology.pydontology.Relation
::: pydontology.pydontology.JSONLDGraph
::: pydontology.pydontology.JSONLDGraph.ontology_graph
::: pydontology.pydontology.JSONLDGraph.shacl_graph
::: pydontology.pydontology.make_model


# Annotation classes
These classes enable use of annotations to provide RDFS/OWL and SHACL metadata
to attributes of the ontology classes, which is then used in the construction
of the ontology graph and SHACL graph.

### Supported RDFS and OWL constructs
Pydontology supports the `rdfs:domain` and `rdfs:range` constructs via annotations.
The `rdfs:subClassOf` construct is added implicitly to an ontology class via inheritance of an another class.
Multiple inheritance is currently not supported, but will be in a future release.

### Supported SHACL constructs
Pydontology supports the following SHACL constructs via annotations:

- **Value Type Constraints**: `sh:datatype`, `sh:nodeKind`, `sh:class`
- **Cardinality Constraints**: `sh:minCount`, `sh:maxCount`
- **String-based Constraints**: `sh:pattern`, `sh:minLength`, `sh:maxLength`
- **Value Range Constraints**: `sh:minInclusive`, `sh:maxInclusive`, `sh:minExclusive`, `sh:maxExclusive`

::: pydontology.rdfs.RDFSAnnotation
    options:
      filters:
        - "!DOMAIN"
        - "!RANGE"

::: pydontology.shacl.SHACLAnnotation
    options:
      filters:
      #Add filters for the shacl dataclasses AI!
