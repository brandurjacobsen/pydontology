import warnings
from inspect import get_annotations
from types import UnionType
from typing import List, Literal, Optional, get_args

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.json_schema import SkipJsonSchema

from .owl import OWLAnnotation
from .rdfs import RDFSAnnotation
from .settings import Settings
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
    sameAs: Optional[Relation] = Field(
        default=None,
        alias="owl:sameAs",
        description="All statements about this class hold for the other.",
    )
    equivalentClass: Optional[Relation] = Field(
        default=None,
        alias="owl:equivalentClass",
        description="Members of this class are also members of the other",
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class _OntologyProperty(BaseModel):
    """Represents an OWL property in an ontology graph."""

    id: str = Field(alias="@id", description="Property IRI")
    # type: Literal["owl:ObjectProperty", "owl:DatatypeProperty"] = Field(alias="@type")
    type: List[
        Literal[
            "owl:ObjectProperty",
            "owl:DatatypeProperty",
            "owl:TransitiveProperty",
            "owl:SymmetricProperty",
            "owl:FunctionalProperty",
            "owl:InverseFunctionalProperty",
            "owl:InverseProperty",
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
        default=None, alias="rdfs:subPropertyOf", description="IRI of superproperty"
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
    # Map Python types to xml schema types
    type_map = {
        "str": "xsd:string",
        "int": "xsd:integer",
        "float": "xsd:decimal",
        "bool": "xsd:boolean",
        "datetime": "xsd:dateTimeStamp",
    }

    cfg = Settings()

    def __init__(self, ontology: UnionType):
        print(self.cfg)
        # Check that the classes given in the UnionType inherit from Entity class
        self._entities = get_args(ontology)
        for cls in self._entities:
            if not issubclass(cls, Entity):
                raise TypeError(
                    f"Expected subclass of 'Entity', got {cls} with type '{type(cls)}'"
                )

        # Construct a dict that maps Entity class names to class metadata
        self._edb = dict()

        # Construct a dict that maps field names to field metadata
        self._pdb = dict()

        for e in self._entities:
            class_name = e.__name__
            description = e.__doc__.strip() if e.__doc__ else None
            parent = e.__mro__[1].__name__ if e.__mro__[1] != Entity else None

            local_fields = get_annotations(e).keys()
            all_fields = e.model_fields.keys()

            self._edb[class_name] = {
                "description": description,
                "parent": parent,
                "local_fields": local_fields,
                "all_fields": all_fields,
            }

            for field_name, field_info in e.model_fields.items():
                if field_name not in local_fields:
                    continue

                is_required = field_info.is_required()

                if is_required:
                    field_type = field_info.annotation.__name__
                else:
                    field_type = get_args(field_info.annotation)[0].__name__

                # In case the same field name is used several times in ontology
                if field_name in self._pdb:
                    defined_in = self._pdb[field_name]["defined_in"]
                    if field_info.alias != self._pdb[field_name]["alias"]:
                        raise Exception(
                            (
                                f"Field name '{field_name}' defined in '{class_name}'",
                                f"must have same alias as '{field_name}' defined in '{defined_in}'",
                            )
                        )
                    elif field_type != self._pdb[field_name]["field_type"]:
                        raise Exception(
                            (
                                f"Field name '{field_name}' defined in '{class_name}'",
                                f"must have same type as '{field_name}' defined in '{defined_in}'",
                            )
                        )
                    elif sorted(field_info.metadata, key=lambda x: str(x)) != sorted(
                        self._pdb[field_name]["metadata"], key=lambda x: str(x)
                    ):
                        raise Exception(
                            (
                                f"Field name '{field_name}' defined in '{class_name}'",
                                f"must have same metadata as '{field_name}' defined in '{defined_in}'",
                            )
                        )

                    # Set 'is_duplicate' to True in _pdb dict
                    self._pdb[field_name]["is_duplicate"] = True

                    # Concatenate field descriptions if descriptions are not identical
                    if self._pdb[field_name]["description"] == field_info.description:
                        continue

                    if self.cfg.DESCRIPTION_AS_COMMENT and self.cfg.CONCAT_COMMENTS:
                        warnings.warn(
                            f"""Field name '{field_name}' defined in '{class_name}',
                            has different description than '{field_name}' defined in '{defined_in}'.
                            Descriptions will be concatenated using '|' as separator."""
                        )

                        self._pdb[field_name]["description"] = (
                            self._pdb[field_name]["description"]
                            + " | "
                            + field_info.description
                        )
                    elif self.cfg.DESCRIPTION_AS_COMMENT:
                        warnings.warn(
                            f"""Field name '{field_name}' defined in '{class_name}',
                            has different description than '{field_name}' defined in '{defined_in}'.
                            Last seen description will be used."""
                        )
                        self._pdb[field_name]["description"] = field_info.description

                else:
                    field_map = {
                        "defined_in": class_name,
                        "is_required": is_required,
                        "is_relation": field_type == "Relation",
                        "is_duplicate": False,
                        "field_type": field_type,
                        "description": field_info.description,
                        "alias": field_info.alias,
                        "metadata": field_info.metadata,
                    }
                    self._pdb[field_name] = field_map

    def ontology_graph(self, context: BaseContext = BaseContext()):
        """Generate ontology graph"""

        ontology_classes = []

        # Build ontology class definitions
        for class_name, class_info in self._edb.items():
            class_fields = dict()
            class_fields["id"] = class_name
            class_fields["label"] = class_name
            class_fields["comment"] = class_info["description"]
            if class_info["parent"] != None:
                class_fields["subClassOf"] = Relation(id=class_info["parent"])
            else:
                class_fields["subClassOf"] = Relation(id="owl:Thing")
            class_def = _OntologyClass.model_validate(class_fields)
            ontology_classes.append(class_def)

        # Build ontology property definitions
        for field_name, field_info in self._pdb.items():
            prop_fields = dict()
            if field_info["is_relation"]:
                prop_fields["type"] = ["owl:ObjectProperty"]
            else:
                prop_fields["type"] = ["owl:DatatypeProperty"]
            if field_info["is_duplicate"]:
                prop_fields["domain"] = None
            else:
                prop_fields["domain"] = Relation(id=field_info["defined_in"])
            prop_fields["id"] = field_name
            prop_fields["label"] = field_name
            prop_fields["comment"] = field_info["description"]
            prop_fields["range"] = None

            prop_def = _OntologyProperty.model_validate(prop_fields)

            for meta in field_info["metadata"]:
                if isinstance(meta, RDFSAnnotation.RANGE):
                    prop_def.range = Relation(id=meta.value)
                elif isinstance(meta, RDFSAnnotation.DOMAIN):
                    prop_def.domain = Relation(id=meta.value)
                elif isinstance(meta, RDFSAnnotation.SUB_PROPERTY_OF):
                    prop_def.subPropertyOf = Relation(id=meta.value)
                elif isinstance(meta, OWLAnnotation.FUNCTIONAL_PROPERTY):
                    prop_def.type.append("owl:FunctionalProperty")
                # Fill in the remaining annotations fit for @type AI!
            ontology_classes.append(prop_def)

        return JSONLDGraph(context=context, graph=ontology_classes)

    def shacl_graph(self):
        """Generate SHACL graph"""

        shacl_shapes = []

        for class_name, class_info in self._edb.items():
            property_shapes = []

            for field_name, field_info in self._pdb.items():
                if field_name not in class_info["all_fields"]:
                    continue

                shape_fields = {
                    "id": f"{class_name}Shape_{field_name}",
                    "path": Relation(id=field_name),
                    "name": field_name,
                    "description": field_info["description"],
                }

                prop_shape = _PropertyShape.model_validate(shape_fields)

                if field_info["is_relation"]:
                    prop_shape.nodeKind = Relation(id="sh:IRI")
                else:
                    prop_shape.datatype = Relation(
                        id=self.type_map[field_info["field_type"]]
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

            node_fields = {
                "id": f"{class_name}Shape",
                "targetClass": Relation(id=class_name),
                "property": property_shapes,
            }

            node_shape = _NodeShape.model_validate(node_fields)
            shacl_shapes.append(node_shape)

        return JSONLDGraph(context=BaseContext(), graph=shacl_shapes)

    def jsonld_graph(self, context: BaseContext = BaseContext(), graph=[]):
        return JSONLDGraph(context=context, graph=graph)
