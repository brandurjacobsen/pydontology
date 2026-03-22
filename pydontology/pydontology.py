from inspect import get_annotations
from types import UnionType
from typing import List, Literal, Optional, get_args

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.json_schema import SkipJsonSchema

from .rdfs import RDFSAnnotation
from .shacl import SHACLAnnotation


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
    """Represents an RDFS/OWL class in an ontology.

    Args:
        id (str): The IRI identifier for the class (mapped to @id in JSON-LD)
        type (Literal["rdfs:Class"]): The RDF type, always "rdfs:Class" (mapped to @type)
        label (str): Human-readable label for the class (mapped to rdfs:label)
        comment (Optional[str]): Optional description/comment for the class (mapped to rdfs:comment)
        subClassOf (Optional[Relation]): Optional parent class relationship (mapped to rdfs:subClassOf)
    """

    id: str = Field(alias="@id", description="Class IRI")
    type: Literal["rdfs:Class"] = Field(default="rdfs:Class", alias="@type")
    label: str = Field(alias="rdfs:label", description="Human-readable label")
    comment: Optional[str] = Field(
        default=None, alias="rdfs:comment", description="Class description"
    )
    subClassOf: Optional[Relation] = Field(
        default=None, alias="rdfs:subClassOf", description="Parent class IRI"
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class _OntologyProperty(BaseModel):
    """Represents an OWL property in an ontology.

    Args:
        id (str): The IRI identifier for the property (mapped to @id in JSON-LD)
        type (Literal["owl:ObjectProperty", "owl:DatatypeProperty"]): The property type (mapped to @type)
        label (str): Human-readable label for the property (mapped to rdfs:label)
        domain (Relation): Domain class IRI (mapped to rdfs:domain)
        range (Optional[Relation]): Optional range class or datatype IRI (mapped to rdfs:range)
        comment (Optional[str]): Optional property description (mapped to rdfs:comment)
    """

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
    """Represents a SHACL property shape.

    Args:
        id (str): The IRI identifier for the property shape (mapped to @id in JSON-LD)
        type (Literal["sh:PropertyShape"]): The shape type, always "sh:PropertyShape" (mapped to @type)
        path (Relation): Property path (mapped to sh:path)
        datatype (Optional[Relation]): Expected datatype (mapped to sh:datatype)
        shclass (Optional[Relation]): Expected class (mapped to sh:class)
        nodeKind (Optional[Relation]): Node kind constraint (mapped to sh:nodeKind)
        minCount (Optional[int]): Minimum cardinality (mapped to sh:minCount)
        maxCount (Optional[int]): Maximum cardinality (mapped to sh:maxCount)
        pattern (Optional[str]): Pattern constraint (mapped to sh:pattern)
        minLength (Optional[int]): Minimum length (mapped to sh:minLength)
        maxLength (Optional[int]): Maximum length (mapped to sh:maxLength)
        minInclusive (Optional[float]): Minimum inclusive value (mapped to sh:minInclusive)
        maxInclusive (Optional[float]): Maximum inclusive value (mapped to sh:maxInclusive)
        minExclusive (Optional[float]): Minimum exclusive value (mapped to sh:minExclusive)
        maxExclusive (Optional[float]): Maximum exclusive value (mapped to sh:maxExclusive)
        name (Optional[str]): Human-readable name (mapped to sh:name)
        description (Optional[str]): Property description (mapped to sh:description)
    """

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
    """Represents a SHACL node shape.

    Args:
        id (str): The IRI identifier for the node shape (mapped to @id in JSON-LD)
        type (Literal["sh:NodeShape"]): The shape type, always "sh:NodeShape" (mapped to @type)
        targetClass (Relation): Target class (mapped to sh:targetClass)
        property (List[_PropertyShape]): List of property shapes (mapped to sh:property)
        closed (Optional[bool]): Whether shape is closed (mapped to sh:closed)
        ignoredProperties (Optional[List[Relation]]): Properties to ignore when closed (mapped to sh:ignoredProperties)
    """

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

    This is the return type of the make_model() function, and
    ontology_graph(), shacl_graph() class methods.
    This class serializes as a JSON-LD document/graph.
    """

    context: SkipJsonSchema[dict] = Field(
        default={
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/",
        },
        alias="@context",
        title="@context",
        description="JSON-LD context (alias: @context)",
    )

    graph: List = Field(
        default=[],
        alias="@graph",
        title="@graph",
        description="Default graph containing Entity instances, or subclasses thereof (alias: @graph)",
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class Pydontology:
    def __init__(self, ontology: UnionType):
        entities = get_args(ontology)
        for cls in entities:
            if not issubclass(cls, Entity):
                raise TypeError(
                    f"Expected subclass of Entity, got {cls} with type {type(cls)}"
                )
        self.db = dict()
        for e in entities:
            # Set 'description' to docstring.
            # Set 'fields' to Pydantic model fields that are in class annotations
            # Set 'parent' to first non-Entity superclass in the MRO
            model_fields = e.model_fields
            annotations = get_annotations(e)
            self.db[e.__name__] = {
                "description": e.__doc__.strip() if e.__doc__ else None,
                "fields": {
                    k: v for k, v in e.model_fields.items() if k in get_annotations(e)
                },
                "all_fields": {k: v for k, v in e.model_fields.items()},
                "parent": e.__mro__[1].__name__ if e.__mro__[1] != Entity else None,
            }

    def ontology_graph(self):
        """Generate ontology graph"""
        ontology_classes = []
        ontology_props = set()

        for class_name, class_info in self.db.items():
            # Build class definitions
            class_def = _OntologyClass(
                id=class_name,
                label=class_name,
                comment=class_info["description"],
                subClassOf=Relation(id=class_info["parent"])
                if class_info["parent"]
                else None,
            )  # pyright: ignore
            ontology_classes.append(class_def)

            # Build property definitions
            for field_name, field_info in class_info["fields"].items():
                if field_name in ontology_props:
                    # TODO:
                    # Compare props and ensure that only 'description' differs
                    # If identical, skip
                    continue  # Skip for now...
                ontology_props.add(field_name)
                is_relation = "Relation" in str(field_info.annotation)
                prop_def = _OntologyProperty(
                    id=field_name,  # pyright: ignore
                    type="owl:ObjectProperty"  # pyright: ignore
                    if is_relation
                    else "owl:DatatypeProperty",
                    label=field_name,
                    domain=Relation(id=class_name),
                    comment=field_info.description,
                    range=None,
                )  # pyright: ignore
                ontology_classes.append(prop_def)
                # Add RDFSAnnotation if present
                if field_info.metadata:
                    for annotation in field_info.metadata:
                        if isinstance(annotation, RDFSAnnotation.DOMAIN):
                            prop_def.domain = Relation(id=annotation.value)
                        if isinstance(annotation, RDFSAnnotation.RANGE):
                            prop_def.range = Relation(id=annotation.value)

        # Build context
        vocab = "http://example.com/vocab/"
        ontology_context = {
            "@vocab": vocab,
            "@base": vocab,
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
        }
        return JSONLDGraph(context=ontology_context, graph=ontology_classes)

    def shacl_graph(self):
        """Generate SHACL graph"""
        shacl_shapes = []
        datatype_map = {
            "str": "xsd:string",
            "int": "xsd:integer",
            "float": "xsd:decimal",
            "bool": "xsd:boolean",
        }
        for class_name, class_info in self.db.items():
            property_shapes = []
            for field_name, field_info in class_info["fields"].items():
                prop_shape = _PropertyShape(
                    id=f"{class_name}Shape_{field_name}",
                    path=Relation(id=field_name),
                    name=field_name,
                    description=field_info.description,
                )
                # Check if field is a Relation type
                annotation_str = str(field_info.annotation)
                if "Relation" in annotation_str:
                    prop_shape.nodeKind = Relation(id="sh:IRI")
                else:
                    # Map basic Python types to XSD datatypes
                    type_name = (
                        annotation_str.replace("typing.", "")
                        .replace("Optional[", "")
                        .replace("]", "")
                    )
                    if type_name in datatype_map:
                        prop_shape.datatype = Relation(id=datatype_map[type_name])

                # Required/Optional
                if field_info.is_required:
                    prop_shape.minCount = 1
                else:
                    prop_shape.minCount = None

                # SHACLAnnotation if present
                if field_info.metadata:
                    for annotation in field_info.metadata:
                        if isinstance(annotation, SHACLAnnotation.DATATYPE):
                            prop_shape.datatype = Relation(id=annotation.value)
                        elif isinstance(annotation, SHACLAnnotation.MAX_COUNT):
                            prop_shape.maxCount = annotation.value
                        elif isinstance(annotation, SHACLAnnotation.MIN_COUNT):
                            prop_shape.minCount = annotation.value
                        elif isinstance(annotation, SHACLAnnotation.PATTERN):
                            prop_shape.pattern = annotation.value
                        elif isinstance(annotation, SHACLAnnotation.MIN_LENGTH):
                            prop_shape.minLength = annotation.value
                        elif isinstance(annotation, SHACLAnnotation.MAX_LENGTH):
                            prop_shape.maxLength = annotation.value
                        elif isinstance(annotation, SHACLAnnotation.MIN_INCLUSIVE):
                            prop_shape.minInclusive = annotation.value
                        elif isinstance(annotation, SHACLAnnotation.MAX_INCLUSIVE):
                            prop_shape.maxInclusive = annotation.value
                        elif isinstance(annotation, SHACLAnnotation.MIN_EXCLUSIVE):
                            prop_shape.minExclusive = annotation.value
                        elif isinstance(annotation, SHACLAnnotation.MAX_EXCLUSIVE):
                            prop_shape.maxExclusive = annotation.value
                        elif isinstance(annotation, SHACLAnnotation.NODE_KIND):
                            prop_shape.nodeKind = Relation(id=annotation.value)
                        elif isinstance(annotation, SHACLAnnotation.CLASS):
                            prop_shape.shclass = Relation(id=annotation.value)

                property_shapes.append(prop_shape)

            node_shape = _NodeShape(
                id=f"{class_name}Shape",
                targetClass=Relation(id=class_name),
                property=property_shapes,
            )
            shacl_shapes.append(node_shape)

        vocab = "http://example.com/vocab/"
        shacl_context = {
            "@vocab": vocab,
            "@base": vocab,
            "sh": "http://www.w3.org/ns/shacl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        }
        return JSONLDGraph(context=shacl_context, graph=shacl_shapes)
