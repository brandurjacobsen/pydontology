# Core classes and methods
::: pydontology.pydontology.Entity
::: pydontology.pydontology.Relation
::: pydontology.pydontology.Pydontology
::: pydontology.pydontology.Pydontology.ontology_graph
::: pydontology.pydontology.Pydontology.shacl_graph
::: pydontology.pydontology.Pydontology.jsonld_graph

# Controlling behaviour
::: pydontology.settings.Settings

# Annotation classes
These classes enable use of annotations to provide RDFS/OWL and SHACL metadata
to attributes of the ontology classes, which is then used in the construction
of the ontology graph and SHACL graph.

## Supported RDFS constructs
Pydontology supports the following RDFS constructs via annotations:

- **Class Relationships**: `rdfs:subClassOf` - class inheritance relationships
- **Property Relationships**: `rdfs:subPropertyOf` - property inheritance relationships  
- **Property Constraints**: `rdfs:domain`, `rdfs:range` - property domain and range constraints
- **Documentation**: `rdfs:comment`, `rdfs:label` - human-readable descriptions
- **External References**: `rdfs:seeAlso`, `rdfs:isDefinedBy` - links to external resources

::: pydontology.rdfs.RDFSAnnotation
    options:
      filters:
        - "!DOMAIN"
        - "!RANGE"
        - "!COMMENT"
        - "!IS_DEFINED_BY"
        - "!LABEL"
        - "!SEE_ALSO"
        - "!SUB_CLASS_OF"
        - "!SUB_PROPERTY_OF"

## Supported OWL constructs
Pydontology supports the following OWL constructs via annotations:

- **Class Equivalence**: `owl:equivalentClass` - class equivalence relationships
- **Individual Equivalence**: `owl:sameAs` - individual equivalence relationships
- **Property Equivalence**: `owl:equivalentProperty` - property equivalence relationships
- **Property Relationships**: `owl:inverseOf` - inverse property relationships
- **Property Characteristics**: `owl:TransitiveProperty`, `owl:SymmetricProperty`, `owl:FunctionalProperty`, `owl:InverseFunctionalProperty`
- **Property Types**: `owl:ObjectProperty`, `owl:DatatypeProperty` - explicit property type declarations

::: pydontology.owl.OWLAnnotation
    options:
      filters:
        - "!EQUIVALENT_CLASS"
        - "!SAME_AS"
        - "!EQUIVALENT_PROPERTY"
        - "!INVERSE_OF"
        - "!TRANSITIVE_PROPERTY"
        - "!SYMMETRIC_PROPERTY"
        - "!FUNCTIONAL_PROPERTY"
        - "!INVERSE_FUNCTIONAL_PROPERTY"
        - "!OBJECT_PROPERTY"
        - "!DATATYPE_PROPERTY"

## Supported SHACL constructs
Pydontology supports the following SHACL constructs via annotations:

- **Value Type Constraints**: `sh:datatype`, `sh:nodeKind`, `sh:class`
- **Cardinality Constraints**: `sh:minCount`, `sh:maxCount`
- **Value Range Constraints**: `sh:minInclusive`, `sh:maxInclusive`, `sh:minExclusive`, `sh:maxExclusive`
- **String-based Constraints**: `sh:pattern`, `sh:minLength`, `sh:maxLength`, `sh:languageIn`, `sh:uniqueLang`
- **Property Pair Constraints**: `sh:equals`, `sh:disjoint`, `sh:lessThan`, `sh:lessThanOrEquals`
- **Other Constraints**: `sh:closed`, `sh:ignoredProperties`, `sh:hasValue`, `sh:in`
- **Validation Parameters**: `sh:severity`
- **Documentation**: `sh:name`, `sh:description`

::: pydontology.shacl.SHACLAnnotation
    options:
      filters:
        - "!DATATYPE"
        - "!MAX_COUNT"
        - "!MIN_COUNT"
        - "!PATTERN"
        - "!MIN_LENGTH"
        - "!MAX_LENGTH"
        - "!MIN_INCLUSIVE"
        - "!MAX_INCLUSIVE"
        - "!MIN_EXCLUSIVE"
        - "!MAX_EXCLUSIVE"
        - "!NODE_KIND"
        - "!CLASS"
        - "!CLOSED"        
        - "!DESCRIPTION"        
        - "!DISJOINT"        
        - "!EQUALS"        
        - "!HAS_VALUE"        
        - "!IGNORED_PROPERTIES"        
        - "!IN"        
        - "!LANGUAGE_IN"        
        - "!LESS_THAN"        
        - "!LESS_THAN_OR_EQUALS"        
        - "!NAME"        
        - "!SEVERITY"
        - "!UNIQUE_LANG"
