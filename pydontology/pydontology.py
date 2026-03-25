from inspect import get_annotations
from types import UnionType
from typing import List, Literal, Optional, get_args

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.json_schema import SkipJsonSchema

from .rdfs import RDFSAnnotation
from .shacl import SHACLAnnotation


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

    id: str = Field(alias="@id", title="@id", description="IRI (possibly relative)")
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class Entity(BaseModel):
    """The base class of all ontology classes."""

    id: str = Field(alias="@id", description="IRI (possibly relative)", title="@id")

    @computed_field(alias="@type", title="@type", description="JSON-LD @type")
    @property
    def type(self) -> str:
        return type(self).__name__

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class _OntologyClass(BaseModel):
    """Represents an RDFS/OWL class in an ontology graph"""

    id: str = Field(alias="@id", description="Class IRI")
    type: Literal["rdfs:Class"] = Field(
        default="rdfs:Class",
        alias="@type",
        description="The RDF type. Always 'rdfs:Class'",
    )
    label: str = Field(alias="rdfs:label", description="Human-readable label")
    comment: Optional[str] = Field(
        default=None, alias="rdfs:comment", description="Class description"
    )
    subClassOf: Optional[Relation] = Field(
        default=None, alias="rdfs:subClassOf", description="Parent class IRI"
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class _OntologyProperty(BaseModel):
    """Represents an OWL property in an ontology graph."""

    id: str = Field(alias="@id", description="Property IRI")
    type: Literal["owl:ObjectProperty", "owl:DatatypeProperty"] = Field(alias="@type")
    label: str = Field(alias="rdfs:label", description="Human-readable label")
    domain: Relation = Field(alias="rdfs:domain", description="Domain class IRI")
    range: Optional[Relation] = Field(
        default=None, alias="rdfs:range", description="Range class or datatype IRI"
    )
    comment: Optional[str] = Field(
        default=None, alias="rdfs:comment", description="Property description"
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class _PropertyShape(BaseModel):
    """Represents a SHACL property shape in a SHACL graph."""

    id: str = Field(alias="@id", description="Property shape IRI")
    type: Literal["sh:PropertyShape"] = Field(default="sh:PropertyShape", alias="@type")
    path: Relation = Field(alias="sh:path", description="Property path")
    datatype: Optional[Relation] = Field(
        default=None, alias="sh:datatype", description="Expected datatype"
    )
    shclass: Optional[Relation] = Field(
        default=None, alias="sh:class", description="Expected class"
    )
    nodeKind: Optional[Relation] = Field(
        default=None, alias="sh:nodeKind", description="Node kind constraint"
    )
    minCount: Optional[int] = Field(
        default=None, alias="sh:minCount", description="Minimum cardinality"
    )
    maxCount: Optional[int] = Field(
        default=None, alias="sh:maxCount", description="Maximum cardinality"
    )
    pattern: Optional[str] = Field(
        default=None, alias="sh:pattern", description="Pattern constraint"
    )
    minLength: Optional[int] = Field(
        default=None, alias="sh:minLength", description="Minimum length"
    )
    maxLength: Optional[int] = Field(
        default=None, alias="sh:maxLength", description="Maximum length"
    )
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
    name: Optional[str] = Field(
        default=None, alias="sh:name", description="Human-readable name"
    )
    description: Optional[str] = Field(
        default=None, alias="sh:description", description="Property description"
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
    """Class that encapsulates a JSON-LD document/graph.

    This is the return type of the Pydontology jsonld_graph(), ontology_graph(), shacl_graph() class methods.
    This class serializes as a JSON-LD document/graph.
    """

    context: SkipJsonSchema[BaseContext] = Field(
        default=BaseContext(),
        alias="@context",
        title="@context",
        description="JSON-LD context",
    )

    graph: List = Field(
        default=[],
        alias="@graph",
        title="@graph",
        description="Default graph",
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class Pydontology:
    def __init__(self, ontology: UnionType):
        self.entities = get_args(ontology)
        for cls in self.entities:
            if not issubclass(cls, Entity):
                raise TypeError(
                    f"Expected subclass of 'Entity', got {cls} with type '{type(cls)}'"
                )
        self.db = dict()

        """Construct a dict with entity names as keys
        and dict of field metadata as values."""

        for e in self.entities:
            class_name = e.__name__
            description = e.__doc__.strip() if e.__doc__ else None
            parent = e.__mro__[1].__name__ if e.__mro__[1] != Entity else None
            self.db[class_name] = {
                "description": description,
                "parent": parent,
                "fields": dict(),
            }
            local_annotations = get_annotations(e)
            for field_name, field_info in e.model_fields.items():
                is_local = field_name in local_annotations
                is_required = field_info.is_required()
                is_relation = "Relation" in str(field_info.annotation)
                description = field_info.description

                if is_required:
                    field_type = field_info.annotation.__name__
                else:
                    field_type = get_args(field_info.annotation)[0].__name__

                if field_info.metadata:
                    metadata = field_info.metadata
                else:
                    metadata = []

                field_dict = {
                    "is_local": is_local,
                    "is_required": is_required,
                    "field_type": field_type,
                    "is_relation": is_relation,
                    "description": description,
                    "metadata": metadata,
                }

                self.db[class_name]["fields"][field_name] = field_dict

    def ontology_graph(self):
        """Generate ontology graph"""

        ontology_classes = []
        ontology_props = set()

        for class_name, class_info in self.db.items():
            # Build Ontology class definitions
            class_def = _OntologyClass(
                id=class_name,
                label=class_name,
                comment=class_info["description"],
                subClassOf=Relation(id=class_info["parent"])
                if class_info["parent"]
                else None,
            )
            ontology_classes.append(class_def)

            # Build property definitions
            for field_name, field_info in class_info["fields"].items():
                if not field_info["is_local"]:
                    continue
                if field_name in ontology_props:
                    # TODO:
                    # Compare props and ensure that only 'description' differs
                    # If identical, skip
                    continue  # Skip for now...
                ontology_props.add(field_name)

                prop_def = _OntologyProperty(
                    id=field_name,
                    type="owl:ObjectProperty"
                    if field_info["is_relation"]
                    else "owl:DatatypeProperty",
                    label=field_name,
                    domain=Relation(id=class_name),
                    comment=field_info["description"],
                    range=None,
                )

                for meta in field_info["metadata"]:
                    if isinstance(meta, RDFSAnnotation.RANGE):
                        prop_def.range = Relation(id=meta.value)
                    elif isinstance(meta, RDFSAnnotation.DOMAIN):
                        prop_def.domain = Relation(id=meta.value)

                ontology_classes.append(prop_def)

        return JSONLDGraph(context=BaseContext(), graph=ontology_classes)

    def shacl_graph(self):
        """Generate SHACL graph"""

        shacl_shapes = []

        # Map Python types to xml schema types
        type_map = {
            "str": "xsd:string",
            "int": "xsd:integer",
            "float": "xsd:decimal",
            "bool": "xsd:boolean",
            "datetime": "xsd:dateTimeStamp",
        }

        for class_name, class_info in self.db.items():
            property_shapes = []

            for field_name, field_info in class_info["fields"].items():
                # Skip id and type special fields
                if field_name in ["id", "type"]:
                    continue
                prop_shape = _PropertyShape(
                    id=f"{class_name}Shape_{field_name}",
                    path=Relation(id=field_name),
                    name=field_name,
                    description=field_info["description"],
                )

                if field_info["is_relation"]:
                    prop_shape.nodeKind = Relation(id="sh:IRI")
                else:
                    prop_shape.datatype = Relation(
                        id=type_map[field_info["field_type"]]
                    )

                # Required/Optional
                if field_info["is_required"]:
                    prop_shape.minCount = 1
                else:
                    prop_shape.minCount = None

                for meta in field_info["metadata"]:
                    if isinstance(meta, SHACLAnnotation.DATATYPE):
                        prop_shape.datatype = Relation(id=meta.value)
                    elif isinstance(meta, SHACLAnnotation.MAX_COUNT):
                        prop_shape.maxCount = meta.value
                    elif isinstance(meta, SHACLAnnotation.MIN_COUNT):
                        prop_shape.minCount = meta.value
                    elif isinstance(meta, SHACLAnnotation.PATTERN):
                        prop_shape.pattern = meta.value
                    elif isinstance(meta, SHACLAnnotation.MIN_LENGTH):
                        prop_shape.minLength = meta.value
                    elif isinstance(meta, SHACLAnnotation.MAX_LENGTH):
                        prop_shape.maxLength = meta.value
                    elif isinstance(meta, SHACLAnnotation.MIN_INCLUSIVE):
                        prop_shape.minInclusive = meta.value
                    elif isinstance(meta, SHACLAnnotation.MAX_INCLUSIVE):
                        prop_shape.maxInclusive = meta.value
                    elif isinstance(meta, SHACLAnnotation.MIN_EXCLUSIVE):
                        prop_shape.minExclusive = meta.value
                    elif isinstance(meta, SHACLAnnotation.MAX_EXCLUSIVE):
                        prop_shape.maxExclusive = meta.value
                    elif isinstance(meta, SHACLAnnotation.NODE_KIND):
                        prop_shape.nodeKind = Relation(id=meta.value)
                    elif isinstance(meta, SHACLAnnotation.CLASS):
                        prop_shape.shclass = Relation(id=meta.value)
                property_shapes.append(prop_shape)

            node_shape = _NodeShape(
                id=f"{class_name}Shape",
                targetClass=Relation(id=class_name),
                property=property_shapes,
            )
            shacl_shapes.append(node_shape)

        return JSONLDGraph(context=BaseContext(), graph=shacl_shapes)

    def jsonld_graph(self, context: BaseContext = BaseContext(), graph=[]):
        return JSONLDGraph(context=context, graph=graph)
