from typing import Annotated, Any, List, Literal, Optional

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
)

from .validators import val_no_whitespace


class BaseContext(BaseModel):
    """Default context"""

    version: float = Field(alias="@version", default=1.1)
    vocab: str = Field(
        alias="@vocab",
        default="http://example.com/vocab/",
        description="Prefix of properties, values of @type, and values of terms that are relative.",
    )
    base: str = Field(
        alias="@base",
        default="http://example.com/vocab/",
        description="Prefix of relative IRIs.",
    )
    language: Optional[str] = Field(
        alias="@language", default="en", description="BCP47 default language identifier"
    )
    sh: Literal["http://www.w3.org/ns/shacl#"] = Field(
        default="http://www.w3.org/ns/shacl#"
    )
    xsd: Literal["http://www.w3.org/2001/XMLSchema#"] = Field(
        default="http://www.w3.org/2001/XMLSchema#"
    )
    rdfs: Literal["http://www.w3.org/2000/01/rdf-schema#"] = Field(
        default="http://www.w3.org/2000/01/rdf-schema#"
    )
    owl: Literal["http://www.w3.org/2002/07/owl#"] = Field(
        default="http://www.w3.org/2002/07/owl#"
    )
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class Relation(BaseModel):
    """This class should be the type of Entity attributes for them to be considered as IRIs."""

    id: Annotated[str, AfterValidator(val_no_whitespace)] = Field(
        alias="@id", title="@id", description="IRI", min_length=1
    )
    model_config = ConfigDict(
        populate_by_name=True, serialize_by_alias=True, frozen=True
    )


class Entity(BaseModel):
    """The base class of all ontology classes."""

    id: Annotated[str, AfterValidator(val_no_whitespace)] = Field(
        alias="@id", description="IRI", title="@id", min_length=1
    )

    @computed_field(alias="@type", title="@type", description="JSON-LD @type")
    @property
    def type(self) -> str:
        return type(self).__name__

    sameAs: Optional[List[Relation]] = Field(
        default=None,
        alias="owl:sameAs",
        description="Same individual(s)",
    )

    differentFrom: Optional[List[Relation]] = Field(
        default=None,
        alias="owl:differentFrom",
        description="Different individual(s)",
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RDFList(BaseModel):
    """An ordered RDF list structure (collection)"""

    list: List[Any] = Field(alias="@list")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class _PropertyShape(BaseModel):
    """Represents a SHACL property shape in a SHACL graph."""

    id: str = Field(alias="@id", description="Property shape IRI")
    type: Literal["sh:PropertyShape"] = Field(default="sh:PropertyShape", alias="@type")
    path: Relation = Field(alias="sh:path", description="Property path")

    # Value Type Constraint Components
    shclass: Optional[Relation] = Field(
        default=None, alias="sh:class", description="Expected class"
    )
    datatype: Optional[Relation] = Field(
        default=None, alias="sh:datatype", description="Expected datatype"
    )
    nodeKind: Optional[Relation] = Field(
        default=None, alias="sh:nodeKind", description="Node kind constraint"
    )
    # Cardinality Constraint Components
    minCount: Optional[int] = Field(
        default=None, alias="sh:minCount", ge=0, description="Minimum cardinality"
    )
    maxCount: Optional[int] = Field(
        default=None, alias="sh:maxCount", ge=0, description="Maximum cardinality"
    )
    # Value Range Constraint Components
    minInclusive: Optional[float] = Field(
        default=None, alias="sh:minInclusive", description="Minimum inclusive value"
    )
    maxInclusive: Optional[float] = Field(
        default=None, alias="sh:maxInclusive", description="Maximum inclusive value"
    )
    minExclusive: Optional[float] = Field(
        default=None, alias="sh:minExclusive", description="Minimum exclusive value"
    )
    maxExclusive: Optional[float] = Field(
        default=None, alias="sh:maxExclusive", description="Maximum exclusive value"
    )
    # String-based Constraint Components
    pattern: Optional[str] = Field(
        default=None, alias="sh:pattern", description="Pattern constraint"
    )
    minLength: Optional[int] = Field(
        default=None, alias="sh:minLength", description="Minimum length"
    )
    maxLength: Optional[int] = Field(
        default=None, alias="sh:maxLength", description="Maximum length"
    )
    languageIn: Optional[List[str]] = Field(
        default=None, alias="sh:languageIn", description="List of allowed language tags"
    )
    uniqueLang: Optional[bool] = Field(
        default=None,
        alias="sh:uniqueLang",
        description="Whether language tags must be unique",
    )
    # Property Pair Constraint Components
    equals: Optional[Relation] = Field(
        default=None, alias="sh:equals", description="Property path with equal values"
    )
    disjoint: Optional[Relation] = Field(
        default=None,
        alias="sh:disjoint",
        description="Property path with disjoint values",
    )
    lessThan: Optional[Relation] = Field(
        default=None,
        alias="sh:lessThan",
        description="Property path with greater values",
    )
    lessThanOrEquals: Optional[Relation] = Field(
        default=None,
        alias="sh:lessThanOrEquals",
        description="Property path with greater or equal values",
    )
    # Other Constraint Components
    closed: Optional[bool] = Field(
        default=None, alias="sh:closed", description="Whether shape is closed"
    )
    ignoredProperties: Optional[List[Relation]] = Field(
        default=None,
        alias="sh:ignoredProperties",
        description="Properties to ignore when closed",
    )
    hasValue: Optional[str | int | float | bool] = Field(
        default=None, alias="sh:hasValue", description="Required value"
    )
    shIn: Optional[List[str | int | float | bool]] = Field(
        default=None, alias="sh:in", description="List of allowed values"
    )

    # Validation parameter constructs
    severity: Optional[Relation] = Field(
        default=None,
        alias="sh:severity",
        description="Severity of constraint violation",
    )

    # Non validating constructs
    name: Optional[str] = Field(
        default=None, alias="sh:name", description="Human-readable name"
    )
    description: Optional[str] = Field(
        default=None, alias="sh:description", description="Property shape description"
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class _NodeShape(BaseModel):
    """Represents a SHACL node shape in a SHACL graph."""

    id: str = Field(alias="@id", description="Node shape IRI")
    type: Literal["sh:NodeShape"] = Field(default="sh:NodeShape", alias="@type")
    targetClass: Relation = Field(alias="sh:targetClass", description="Target class")
    property: List[_PropertyShape] = Field(
        default_factory=list, alias="sh:property", description="Property shapes"
    )
    closed: Optional[bool] = Field(
        default=None, alias="sh:closed", description="Whether shape is closed"
    )
    ignoredProperties: Optional[List[Relation]] = Field(
        default=None,
        alias="sh:ignoredProperties",
        description="Properties to ignore when closed",
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class JSONLDGraph(BaseModel):
    """Class that encapsulates a JSON-LD document/graph."""

    context: BaseContext = Field(
        default=BaseContext(),
        alias="@context",
        title="@context",
        description="JSON-LD context",
    )

    graph: List[Any] = Field(
        default=[],
        alias="@graph",
        title="@graph",
        description="Default or named graph",
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
