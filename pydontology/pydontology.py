import warnings
from inspect import get_annotations, isclass
from types import UnionType
from typing import Annotated, List, Literal, Optional, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.json_schema import SkipJsonSchema

from .owl import OWLAnnotation
from .rdfs import RDFSAnnotation
from .settings import Settings
from .shacl import SHACLAnnotation


class DuplicatePropertyError(Exception):
    """Raised when fields/properties are redefined erroneously"""


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
    type: Literal["rdfs:Class", "owl:Class"] = Field(
        default="rdfs:Class",
        alias="@type",
        description="The RDF type.",
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
        description="All statements about this class/individual hold for the other.",
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
        default=None, alias="rdfs:subPropertyOf", description="IRI of super-property"
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
    severity: Optional[Relation] = Field(
        default=None,
        alias="sh:severity",
        description="Severity of constraint violation",
    )
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

    def __init__(self, ontology: UnionType):
        # Get default settings for ontology_graph and shacl_graph methods
        self.cfg = Settings()

        # Construct a dict that maps Entity class names to class metadata
        self._edb = dict()

        # Construct a dict that maps field names to field metadata
        self._pdb = dict()

        for arg in get_args(ontology):
            cls, metadata = self._get_class_and_metadata(arg)
            class_name = cls.__name__
            description = cls.__doc__.strip() if cls.__doc__ else None
            parent = cls.__mro__[1].__name__ if cls.__mro__[1] != Entity else None

            # Track fields by alias if present else name
            aliased_fields = [
                f
                for f in cls.model_fields.keys()
                if cls.model_fields[f].alias is not None
            ]
            unaliased_fields = [
                f for f in cls.model_fields.keys() if cls.model_fields[f].alias is None
            ]
            all_field_ids = set([*aliased_fields, *unaliased_fields])

            self._edb[class_name] = {
                "description": description,
                "parent": parent,
                "all_field_ids": all_field_ids,
                "metadata": metadata,
            }

            # We use 'get_annotations' and not 'model_fields' because we only
            # want to process fields defined in the current class, not inherited fields
            for field_name in get_annotations(cls).keys():
                field_info = cls.model_fields[field_name]

                if field_info.is_required():
                    assert field_info.annotation is not None
                    field_type = field_info.annotation.__name__
                else:
                    field_type = get_args(field_info.annotation)[0].__name__

                # Fields are identified by alias (if present), otherwise by name in the self._pdb dict.
                # If an ontology class redefines a previously identified property (according to the above),
                # then the Python type needs to be identical, while e.g. default, description, title,
                # examples and SHACL annotation can vary. RDFS/OWL annotations are ignored in redefinitions.

                if field_info.alias is not None and field_info.alias in self._pdb:
                    field_map = self._handle_duplicate_fields(
                        class_name, field_info.alias, field_type, field_info
                    )
                elif field_name in self._pdb:
                    field_map = self._handle_duplicate_fields(
                        class_name, field_name, field_type, field_info
                    )
                else:
                    field_map = {
                        "defined_in": [class_name],
                        "field_type": field_type,
                        "description": [field_info.description],
                        "metadata": [field_info.metadata],
                    }
                    if field_info.alias is not None:
                        self._pdb[field_info.alias] = field_map
                    else:
                        self._pdb[field_name] = field_map

    def _handle_duplicate_fields(self, class_name, field_id, field_type, field_info):
        if field_type != self._pdb[field_id]["field_type"]:
            raise DuplicatePropertyError(
                f"Field {field_id} can not be defined again with different Python type"
            )
        return {
            "defined_in": [class_name, *self._pdb[field_id]["defined_in"]],
            "description": [
                field_info.description,
                *self._pdb[field_id]["description"],
            ],
            "metadata": [field_info.metadata, *self._pdb[field_id]["metadata"]],
            "field_type": field_type,
        }

    def _get_class_and_metadata(self, component):
        origin = get_origin(component)
        if origin is None:
            if not isclass(component) or not issubclass(component, Entity):
                raise TypeError(
                    f"Expected class type. Got {component} with type {type(component)}"
                )
            return (component, None)

        elif origin is Annotated:
            arg = get_args(component)[0]
            if not isclass(arg) or not issubclass(arg, Entity):
                raise TypeError(f"Expected class type. Got {arg} with type {type(arg)}")
            return (arg, component.__metadata__)
        else:
            raise TypeError(f"Unexpected type {type(origin)} in ontology")

    def _add_class_annotations(
        self, class_def: _OntologyClass, annotations: List
    ) -> _OntologyClass:
        """Add class annotations to ontology class"""
        for meta in annotations:
            if isinstance(meta, RDFSAnnotation.COMMENT):
                class_def.comment = meta.value
            elif isinstance(meta, RDFSAnnotation.LABEL):
                class_def.label = meta.value
            elif isinstance(meta, RDFSAnnotation.SUB_CLASS_OF):
                class_def.subClassOf = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, OWLAnnotation.EQUIVALENT_CLASS):
                class_def.equivalentClass = Relation(id=meta.value)  # pyright: ignore
        return class_def

    def _create_ontology_classes(self) -> List[_OntologyClass]:
        """Create ontology classes using _OntologyClass class"""

        ontology_classes = []
        for class_name, class_info in self._edb.items():
            class_fields = dict()
            class_fields["id"] = class_name
            if self.cfg.CLASS_NAME_AS_LABEL:
                class_fields["label"] = class_name
            if self.cfg.DOCSTRING_AS_COMMENT:
                class_fields["comment"] = class_info["description"]
            if class_info["parent"] is not None and self.cfg.SUBCLASS_OF_PARENT:
                class_fields["subClassOf"] = Relation(id=class_info["parent"])  # pyright: ignore
            else:
                if self.cfg.SUBCLASS_OF_DEFAULT is not None:
                    class_fields["subClassOf"] = Relation(
                        id=self.cfg.SUBCLASS_OF_DEFAULT
                    )  # pyright: ignore

            class_def = _OntologyClass.model_validate(class_fields)

            if class_info["metadata"] is not None:
                class_def = self._add_class_annotations(
                    class_def, class_info["metadata"]
                )
            ontology_classes.append(class_def)
        return ontology_classes

    def _add_property_annotations(
        self, prop_def: _OntologyProperty, annotations: List
    ) -> _OntologyProperty:
        """Add property annotations to ontology property"""
        for meta in annotations:
            if isinstance(meta, RDFSAnnotation.RANGE):
                prop_def.range = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, RDFSAnnotation.DOMAIN):
                prop_def.domain = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, RDFSAnnotation.SUB_PROPERTY_OF):
                prop_def.subPropertyOf = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, OWLAnnotation.EQUIVALENT_PROPERTY):
                prop_def.equivalentProperty = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, OWLAnnotation.INVERSE_OF):
                prop_def.inverseOf = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, OWLAnnotation.FUNCTIONAL_PROPERTY):
                if meta.value:
                    prop_def.type.append("owl:FunctionalProperty")
            elif isinstance(meta, OWLAnnotation.INVERSE_FUNCTIONAL_PROPERTY):
                if meta.value:
                    prop_def.type.append("owl:InverseFunctionalProperty")
            elif isinstance(meta, OWLAnnotation.TRANSITIVE_PROPERTY):
                if meta.value:
                    prop_def.type.append("owl:TransitiveProperty")
            elif isinstance(meta, OWLAnnotation.SYMMETRIC_PROPERTY):
                if meta.value:
                    prop_def.type.append("owl:SymmetricProperty")
        return prop_def

    def _create_ontology_properties(self) -> List[_OntologyProperty]:
        """Create ontology properties using _OntologyProperty class"""
        ontology_props = []
        for field_name, field_info in self._pdb.items():
            prop_fields = dict()
            prop_fields["id"] = field_name
            if field_info["field_type"] == "Relation":
                prop_fields["type"] = ["owl:ObjectProperty"]
            else:
                prop_fields["type"] = ["owl:DatatypeProperty"]
            if self.cfg.FIELD_NAME_AS_LABEL:
                prop_fields["label"] = field_name

            if self.cfg.ORIGIN_AS_DOMAIN:
                if len(field_info["defined_in"]) > 1 and self.cfg.SHOW_WARNINGS:
                    warnings.warn(
                        f"The 'ORIGIN_AS_DOMAIN' setting was ignored for '{field_name}' property since it is defined in multiple classes"
                    )
                else:
                    prop_fields["domain"] = Relation(id=field_info["defined_in"][0])  # pyright: ignore
            if self.cfg.DESCRIPTION_AS_COMMENT:
                if len(field_info["description"]) > 1 and self.cfg.SHOW_WARNINGS:
                    warnings.warn(
                        f"The 'DESCRIPTION_AS_COMMENT' setting was ignored for '{field_name}' property since it is defined in multiple classes"
                    )
                else:
                    prop_fields["comment"] = field_info["description"][0]

            prop_def = _OntologyProperty.model_validate(prop_fields)
            if len(field_info["metadata"]) > 1 and self.cfg.SHOW_WARNINGS:
                warnings.warn(
                    f"Only first seen annotation data will be used for {field_name} property since it is defined in multiple classes"
                )
            self._add_property_annotations(prop_def, field_info["metadata"][0])
            ontology_props.append(prop_def)
        return ontology_props

    def ontology_graph(
        self, context: BaseContext = BaseContext(), settings: Settings | None = None
    ):
        """Generate ontology graph"""
        if settings is not None:
            self.cfg = settings
        onto_classes = self._create_ontology_classes()
        onto_props = self._create_ontology_properties()
        return JSONLDGraph(context=context, graph=[*onto_classes, *onto_props])  # pyright: ignore

    def _add_shacl_annotations(
        self, prop_shape: _PropertyShape, annotations: List
    ) -> _PropertyShape:
        for meta in annotations:
            if isinstance(meta, SHACLAnnotation.DATATYPE):
                prop_shape.datatype = Relation(id=meta.value)  # pyright: ignore
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
                prop_shape.nodeKind = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, SHACLAnnotation.CLASS):
                prop_shape.shclass = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, SHACLAnnotation.SEVERITY):
                prop_shape.severity = Relation(id=meta.value)
        return prop_shape

    def _create_property_shapes(self, class_name: str) -> List[_PropertyShape]:
        """Create SHACL property shapes using _PropertyShape class"""

        prop_shapes = []
        for field_name, field_info in self._pdb.items():
            if field_name not in self._edb[class_name]["all_field_ids"]:
                continue
            if class_name in field_info["defined_in"]:
                idx = field_info["defined_in"].index(class_name)
            else:
                idx = 0

            shape_fields = {
                "id": f"{class_name}Shape_{field_name}",
                "path": Relation(id=field_name),  # pyright: ignore
                "name": field_name,
                "description": field_info["description"][idx],
            }

            prop_shape = _PropertyShape.model_validate(shape_fields)

            if field_info["field_type"] == "Relation":
                prop_shape.nodeKind = Relation(id="sh:IRI")  # pyright: ignore
            else:
                prop_shape.datatype = Relation(
                    id=self.type_map[field_info["field_type"]]
                )  # pyright: ignore

            prop_shape = self._add_shacl_annotations(
                prop_shape, field_info["metadata"][idx]
            )
            prop_shapes.append(prop_shape)

        return prop_shapes

    def _create_node_shapes(self) -> List[_NodeShape]:
        node_shapes = []
        for class_name, class_info in self._edb.items():
            property_shapes = self._create_property_shapes(class_name)
            node_fields = {
                "id": f"{class_name}Shape",
                "targetClass": Relation(id=class_name),  # pyright: ignore
                "property": property_shapes,
            }

            node_shape = _NodeShape.model_validate(node_fields)
            node_shapes.append(node_shape)
        return node_shapes

    def shacl_graph(self, settings: Settings | None = None):
        """Generate SHACL graph"""
        if settings is not None:
            self.cfg = settings

        shacl_shapes = self._create_node_shapes()
        return JSONLDGraph(context=BaseContext(), graph=shacl_shapes)  # pyright: ignore

    def jsonld_graph(self, context: BaseContext = BaseContext(), graph=[]):
        return JSONLDGraph(context=context, graph=graph)  # pyright: ignore
