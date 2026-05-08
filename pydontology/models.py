from types import NoneType, UnionType
from typing import (
    Annotated,
    Any,
    List,
    Literal,
    Optional,
    Self,
    Tuple,
    Union,
    get_args,
    get_origin,
)

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    computed_field,
    model_serializer,
    model_validator,
)

from .types import TYPE_SET, infer_xsd_type
from .validators import val_no_whitespace


class BaseContext(BaseModel):
    """Base json-ld context model"""

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


class TypeVal(BaseModel):
    """Class that serializes as an RDF typed value literal"""

    value: Any = Field(alias="@value", description="Value of RDF literal")
    type: Any = Field(alias="@type", description="XML schema type of RDF literal")

    model_config = ConfigDict(
        populate_by_name=True, serialize_by_alias=True, frozen=True
    )


class Restriction(BaseModel):
    """Model defining OWL Restrictions for use with owl:equivalentClass, owl:intersectionOf, etc.."""

    id: Optional[str] = Field(
        alias="@id", default=None, description="Optional restriction IRI"
    )
    type: Literal["owl:Restriction"] = Field(alias="@type", default="owl:Restriction")
    onProperty: Relation = Field(alias="owl:onProperty")
    someValuesFrom: Optional[Relation] = Field(alias="owl:someValuesFrom", default=None)
    allValuesFrom: Optional[Relation] = Field(alias="owl:allValuesFrom", default=None)
    cardinality: Optional[int] = Field(alias="owl:cardinality", default=None)
    minCardinality: Optional[int] = Field(alias="owl:minCardinality", default=None)
    maxCardinality: Optional[int] = Field(alias="owl:maxCardinality", default=None)

    @model_validator(mode="after")
    def mutually_exclusive(self) -> Self:
        """Ensure only one restriction type is specified at a time."""
        restriction_fields = [
            "someValuesFrom",
            "allValuesFrom",
            "cardinality",
            "minCardinality",
            "maxCardinality",
        ]

        # List of optional fields populated
        populated_fields = [
            field
            for field in restriction_fields
            if self.__getattribute__(field) is not None
        ]

        if len(populated_fields) > 1:
            raise ValueError(
                f"Only one restriction type can be specified. Found: {populated_fields}"
            )

        if len(populated_fields) == 0:
            raise ValueError("At least one restriction type must be specified")

        return self

    model_config = ConfigDict(
        populate_by_name=True, serialize_by_alias=True, frozen=True
    )


class RDFList(BaseModel):
    """An ordered RDF list structure (collection)"""

    list: Tuple[Relation | Restriction, ...] = Field(alias="@list")

    model_config = ConfigDict(
        populate_by_name=True, serialize_by_alias=True, frozen=True
    )


class AllDifferent(BaseModel):
    """The OWL AllDifferent class"""

    type: Literal["owl:AllDifferent"] = Field(alias="@type", default="owl:AllDifferent")
    distinctMembers: RDFList = Field(alias="owl:distinctMembers")

    model_config = ConfigDict(
        populate_by_name=True, serialize_by_alias=True, frozen=True
    )


class BaseMetaData(BaseModel):
    """The base class for a owl:Ontology class"""

    id: str = Field(alias="@id", description="IRI of ontology meta-data")
    type: Literal["owl:Ontology"] = Field(alias="@type", default="owl:Ontology")
    comment: Optional[str] = Field(alias="rdfs:comment", default=None)
    label: Optional[str] = Field(alias="rdfs:label", default=None)
    versionInfo: Optional[str] = Field(alias="owl:versionInfo", default=None)
    imports: Optional[Relation] = Field(alias="owl:imports", default=None)

    model_config = ConfigDict(
        populate_by_name=True, serialize_by_alias=True, frozen=True
    )


class Entity(BaseModel):
    """The base class of all ontology classes.

    Serialization behavior is controlled via Settings class.
    """

    _serialize_literals_as_typeval: bool = False
    _type_strict_mode: bool = True

    id: Annotated[str, AfterValidator(val_no_whitespace)] = Field(
        alias="@id", description="IRI", title="@id", min_length=1
    )

    sameAs: Optional[Relation | List[Relation]] = Field(
        default=None,
        alias="owl:sameAs",
        description="Same individual(s)",
    )

    differentFrom: Optional[Relation | List[Relation]] = Field(
        default=None,
        alias="owl:differentFrom",
        description="Different individual(s)",
    )

    @computed_field(alias="@type", title="@type", description="JSON-LD @type")
    @property
    def type(self) -> str:
        return type(self).__name__

    @classmethod
    def _annotation_contains_type(cls, annotation: Any, target: Any) -> bool:
        """Return True if annotation contains target type in nested typing constructs."""
        if annotation is target:
            return True

        origin = get_origin(annotation)
        if origin is Annotated:
            return cls._annotation_contains_type(get_args(annotation)[0], target)

        if origin in (list, List, set, tuple, frozenset):
            return any(
                cls._annotation_contains_type(arg, target)
                for arg in get_args(annotation)
            )

        if origin in (Union, UnionType):
            return any(
                cls._annotation_contains_type(arg, target)
                for arg in get_args(annotation)
                if arg is not NoneType
            )

        return False

    @classmethod
    def _should_wrap_field(cls, field_name: str, field_info) -> bool:
        """Decide whether a field is eligible for TypeVal serialization."""
        if field_name == "id":
            return False
        if cls._annotation_contains_type(field_info.annotation, Relation):
            return False
        if cls._annotation_contains_type(field_info.annotation, TypeVal):
            return False
        return True

    def _wrap_serialized_value(self, raw_value, serialized_value, field_name: str):
        """Wrap scalar values as TypeVal; recurse into lists and honor strict mode."""
        if raw_value is None:
            return serialized_value
        if isinstance(raw_value, (Relation, TypeVal)):
            return serialized_value
        if isinstance(raw_value, list):
            if not isinstance(serialized_value, list):
                return serialized_value
            wrapped = []
            for idx, raw_item in enumerate(raw_value):
                ser_item = (
                    serialized_value[idx] if idx < len(serialized_value) else raw_item
                )
                wrapped.append(
                    self._wrap_serialized_value(raw_item, ser_item, field_name)
                )
            if len(serialized_value) > len(raw_value):
                wrapped.extend(serialized_value[len(raw_value) :])
            return wrapped

        xsd_type = infer_xsd_type(raw_value)
        if xsd_type is None:
            if self._type_strict_mode:
                raise ValueError(
                    f"Field '{field_name}' has value type '{type(raw_value).__name__}' which is not in the type map (Setting: TYPE_STRICT_MODE)"
                )
            return serialized_value
        return TypeVal(value=raw_value, type=xsd_type).model_dump()  # pyright: ignore

    @model_serializer(mode="wrap")
    def _serialize_literals(self, handler):
        """Serialize scalar literals as TypeVal when the global toggle is enabled."""
        data = handler(self)
        if not self._serialize_literals_as_typeval:
            return data

        for field_name, field_info in self.__class__.model_fields.items():
            if not self._should_wrap_field(field_name, field_info):
                continue
            key = field_info.serialization_alias or field_info.alias or field_name
            if key not in data:
                continue
            raw_value = getattr(self, field_name)
            if raw_value is None:
                continue
            data[key] = self._wrap_serialized_value(raw_value, data[key], field_name)

        return data

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class _OntologyClass(BaseModel):
    """Represents an RDFS/OWL class in an ontology graph"""

    id: str = Field(alias="@id", description="Class IRI")
    type: Literal["rdfs:Class", "owl:Class"] = Field(
        default="rdfs:Class",
        alias="@type",
        description="The RDF type.",
    )
    label: Optional[str] = Field(
        alias="rdfs:label", default=None, description="Human-readable label"
    )
    comment: Optional[str] = Field(
        default=None, alias="rdfs:comment", description="Class description"
    )
    subClassOf: Optional[List[Relation | Restriction]] = Field(
        default=None, alias="rdfs:subClassOf", description="Parent class(es)"
    )
    seeAlso: Optional[HttpUrl] = Field(
        default=None, alias="rdfs:seeAlso", description="Link to additional information"
    )
    isDefinedBy: Optional[HttpUrl] = Field(
        default=None, alias="rdfs:isDefinedBy", description="Link to definition"
    )
    equivalentClass: Optional[List[Relation | Restriction]] = Field(
        default=None,
        alias="owl:equivalentClass",
        description="Members of this class are also members of the other",
    )
    intersectionOf: Optional[RDFList] = Field(
        default=None, alias="owl:intersectionOf", description=""
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class _OntologyProperty(BaseModel):
    """Represents an OWL property in an ontology graph."""

    id: str = Field(alias="@id", description="Property IRI")
    type: List[
        Literal[
            "owl:ObjectProperty",
            "owl:DatatypeProperty",
            "owl:TransitiveProperty",
            "owl:SymmetricProperty",
            "owl:FunctionalProperty",
            "owl:InverseFunctionalProperty",
            "owl:InverseProperty",
            *TYPE_SET,
        ]
    ] = Field(alias="@type")
    label: Optional[str] = Field(alias="rdfs:label", description="Human-readable label")
    domain: Optional[Relation] = Field(
        default=None, alias="rdfs:domain", description="Domain class IRI"
    )
    range: Optional[Relation] = Field(
        default=None, alias="rdfs:range", description="Range class or datatype IRI"
    )
    comment: Optional[str] = Field(
        default=None, alias="rdfs:comment", description="Property description"
    )
    subPropertyOf: Optional[Relation] = Field(
        default=None, alias="rdfs:subPropertyOf", description="IRI of super-property"
    )
    seeAlso: Optional[HttpUrl] = Field(
        default=None, alias="rdfs:seeAlso", description="Link to additional information"
    )
    isDefinedBy: Optional[HttpUrl] = Field(
        default=None, alias="rdfs:isDefinedBy", description="Link to definition"
    )
    equivalentProperty: Optional[Relation] = Field(
        default=None,
        alias="owl:equivalentProperty",
        description="IRI of equivalent property",
    )
    inverseOf: Optional[Relation] = Field(
        default=None,
        alias="owl:inverseOf",
        description="Property is the inverse of another property",
    )

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

    ## Other Constraint Components
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

    _all_different = False

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

    def all_different(self, toggle: bool) -> None:
        """Includes the owl:AllDifferent class in the serialization

        All individuals in the graph are then seen as distinct members
        """
        self._all_different = toggle

    @model_serializer(mode="wrap")
    def _serialize_as_all_different(self, handler):
        data = handler(self)
        if not self._all_different:
            return data

        # Include AllDifferent class in graph with graph individuals in 'distinctMembers' RDF collection.
        rdf_list = [Relation(id=i["@id"]) for i in data["@graph"]]  # pyright: ignore
        data["@graph"].append(
            AllDifferent(distinctMembers=RDFList(list=tuple(rdf_list)))  # pyright: ignore
        )
        return data

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
