from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    """Controls the default behaviors of graph generation."""

    model_config = ConfigDict(frozen=True)

    # Whether to show user warnings
    SHOW_WARNINGS: bool = True

    # Use class name as rdfs:label for ontology classes
    CLASS_NAME_AS_LABEL: bool = True

    # Use class docstrings as rdfs:comment for ontology classes
    DOCSTRING_AS_COMMENT: bool = True

    # Use field name as rdfs:label for ontology properties
    FIELD_NAME_AS_LABEL: bool = True

    # Use field descriptions as rdfs:comment for ontology properties
    # (Ignored if property is defined in multiple ontology classes)
    DESCRIPTION_AS_COMMENT: bool = True

    # Use origin class as rdfs:domain for ontology properties
    # (Ignored if property is defined in multiple ontology classes)
    ORIGIN_AS_DOMAIN: bool = True

    # Default parent (rdfs:subClassOf) for ontology classes inheriting from Entity
    DEFAULT_SUBCLASS_OF: str | None = "owl:Thing"

    # Set rdfs:subClassOf to parent class (Recommended)
    SUBCLASS_OF_PARENT: bool = True

    # Use field name (or alias) as sh:name for property shapes
    FIELD_NAME_AS_SH_NAME: bool = True

    # Use field description as sh:description for property shapes
    DESCRIPTION_AS_SH_DESCRIPTION: bool = True

    # Set sh:nodeKind to IRI for property shapes of relations
    RELATION_AS_NODEKIND_IRI: bool = True

    # Use internal typemap of Python types to xsd types to set sh:datatype for SHACL property shapes
    TYPE_AS_SH_DATATYPE: bool = True

    # Attempt to use internal typemap of Python types to xsd types to set rdf:type for properties
    TYPE_AS_RDF_TYPE: bool = True

    # Serialize scalar literals as typed values in JSON-LD data graphs
    LITERALS_AS_TYPEVAL: bool = False

    # Require that Entity class fields can resolve to specific Python type
    # and that redefined properties have same Python type
    TYPE_STRICT_MODE: bool = True

    # Use a default prefix term. If a default prefix is not used,
    # then all properties will need a serialization_alias that
    # serializes as a valid IRI. E.g. a property "knows" would need
    # serialization_alias "ex:knows" or the like.
    DEFAULT_PREFIX: str | None = "ex:"

    # Namespace IRI that DEFAULT_PREFIX maps to in the generated @context.
    # When set (along with DEFAULT_PREFIX), Pydontology injects the mapping
    # into the serialized JSON-LD context so that compact IRIs expand.
    DEFAULT_PREFIX_NS: str | None = None
