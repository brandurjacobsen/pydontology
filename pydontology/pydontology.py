import warnings
from copy import deepcopy
from inspect import get_annotations, isclass
from types import NoneType, UnionType
from typing import Annotated, Any, List, Literal, Optional, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, create_model
from pydantic.fields import FieldInfo

from .models import (
    BaseContext,
    Entity,
    JSONLDGraph,
    Relation,
    _NodeShape,
    _PropertyShape,
)
from .owl import OWLAnnotation, RDFList
from .rdfs import RDFSAnnotation
from .settings import Settings
from .shacl import SHACLAnnotation

TYPE_MAP = {
    "str": "xsd:string",
    "int": "xsd:integer",
    "Decimal": "xsd:decimal",
    "float": "xsd:decimal",  # float after Decimal for INV_TYPE_MAP
    "bool": "xsd:boolean",
    "datetime": "xsd:dateTime",
    "date": "xsd:date",
}
INV_TYPE_MAP = {v: k for k, v in TYPE_MAP.items()}
TYPE_SET = set(TYPE_MAP.values())


class DuplicatePropertyError(Exception):
    """Raised when fields/properties are redefined erroneously"""


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
    subClassOf: Optional[List[Relation | OWLAnnotation.Restriction]] = Field(
        default=None, alias="rdfs:subClassOf", description="Parent class(es)"
    )
    seeAlso: Optional[HttpUrl] = Field(
        default=None, alias="rdfs:seeAlso", description="Link to additional information"
    )
    isDefinedBy: Optional[HttpUrl] = Field(
        default=None, alias="rdfs:isDefinedBy", description="Link to definition"
    )
    equivalentClass: Optional[List[Relation | OWLAnnotation.Restriction]] = Field(
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
        # How can I add the values of TYPE_MAP to the literals AI?
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


class Pydontology:
    type_map = TYPE_MAP

    def __init__(self, ontology: UnionType):
        self.ontology = ontology
        # Get default settings for ontology_graph and shacl_graph methods
        self.cfg = Settings()

        # Construct a dict that maps Entity class names to class metadata
        self._cls_db = dict()

        # Construct a dict that maps field names/properties to field metadata
        self._prop_db = dict()

        origin = get_origin(ontology)
        if origin is Annotated:  # E.g. one annotated class
            components = [ontology]
        elif origin is Union or origin is UnionType:
            components = get_args(ontology)
        else:
            components = [ontology]

        for arg in components:
            cls, metadata = self._get_class_and_metadata(arg)
            class_name = cls.__name__
            description = cls.__doc__.strip() if cls.__doc__ else None
            parent = cls.__mro__[1].__name__ if cls.__mro__[1] != Entity else None

            self._cls_db[class_name] = {
                "description": description,
                "parent": parent,
                "metadata": metadata,
            }

            # We use 'get_annotations' and not 'model_fields' because we only
            # want to process fields defined in the current class, not inherited fields
            for field_name in get_annotations(cls).keys():
                field_info = cls.model_fields[field_name]
                field_type = self._get_field_type(field_info)

                if self.cfg.TYPE_STRICT_MODE:
                    if field_type not in self.type_map and field_type != "Relation":
                        raise ValueError(
                            f"Field '{field_name}' has type '{field_type}' which is not a Relation, nor in the type map (Setting: TYPE_STRICT_MODE)"
                        )

                # Fields are identified by alias (if present), otherwise by name in the self._prop_db dict.
                # If an ontology class redefines a previously identified property (according to the above),
                # then the Python type needs to be identical, while e.g. default, description, title,
                # examples and SHACL annotation can vary.

                if field_info.alias is not None and field_info.alias in self._prop_db:
                    field_map = self._handle_duplicate_fields(
                        class_name, field_info.alias, field_type, field_info
                    )
                elif field_name in self._prop_db:
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
                    self._prop_db[field_info.alias] = field_map
                else:
                    self._prop_db[field_name] = field_map

    def _get_field_type(self, field_info: FieldInfo) -> str | None:
        """Resolve field type to one specific Python type as string or None"""
        annotation = field_info.annotation
        if annotation is None:
            return None

        origin = get_origin(annotation)
        if origin is None:
            return annotation.__name__
        elif origin is Union or origin is UnionType:
            args = get_args(annotation)
            if len(args) == 2 and NoneType in args:
                return args[0].__name__ if args[0] is not NoneType else args[1].__name__

            else:
                return None
        else:
            return None

    def _handle_duplicate_fields(self, class_name, field_id, field_type, field_info):
        if (
            field_type != self._prop_db[field_id]["field_type"]
            and self.cfg.TYPE_STRICT_MODE
        ):
            raise ValueError(
                f"Field {field_id} can not be defined again with different Python type (Setting: TYPE_STRICT_MODE)"
            )
        return {
            "defined_in": [*self._prop_db[field_id]["defined_in"], class_name],
            "description": [
                *self._prop_db[field_id]["description"],
                field_info.description,
            ],
            "metadata": [*self._prop_db[field_id]["metadata"], field_info.metadata],
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
                class_def.subClassOf.append(meta.value)  # pyright: ignore
            elif isinstance(meta, RDFSAnnotation.SEE_ALSO):
                class_def.seeAlso = meta.value
            elif isinstance(meta, RDFSAnnotation.IS_DEFINED_BY):
                class_def.isDefinedBy = meta.value
            elif isinstance(meta, OWLAnnotation.EQUIVALENT_CLASS):
                if class_def.equivalentClass is not None:
                    class_def.equivalentClass.append(meta.value)  # pyright: ignore
                else:
                    class_def.equivalentClass = [meta.value]
            elif isinstance(meta, OWLAnnotation.INTERSECTION_OF):
                class_def.intersectionOf = meta.value

        return class_def

    def _create_ontology_classes(self) -> List[_OntologyClass]:
        """Create ontology classes using _OntologyClass class"""

        ontology_classes = []
        for class_name, class_info in self._cls_db.items():
            class_fields = dict()
            class_fields["id"] = class_name
            if self.cfg.CLASS_NAME_AS_LABEL:
                class_fields["label"] = class_name
            if self.cfg.DOCSTRING_AS_COMMENT:
                class_fields["comment"] = class_info["description"]
            if class_info["parent"] is not None and self.cfg.SUBCLASS_OF_PARENT:
                class_fields["subClassOf"] = [Relation(id=class_info["parent"])]  # pyright: ignore
            else:
                if self.cfg.SUBCLASS_OF_DEFAULT is not None:
                    class_fields["subClassOf"] = [
                        Relation(id=self.cfg.SUBCLASS_OF_DEFAULT)  # pyright: ignore
                    ]

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
            if isinstance(meta, RDFSAnnotation.COMMENT):
                prop_def.comment = meta.value
            if isinstance(meta, RDFSAnnotation.LABEL):
                prop_def.label = meta.value
            if isinstance(meta, RDFSAnnotation.RANGE):
                prop_def.range = meta.value
            elif isinstance(meta, RDFSAnnotation.DOMAIN):
                prop_def.domain = meta.value
            elif isinstance(meta, RDFSAnnotation.SUB_PROPERTY_OF):
                prop_def.subPropertyOf = meta.value
            elif isinstance(meta, RDFSAnnotation.SEE_ALSO):
                prop_def.seeAlso = meta.value
            elif isinstance(meta, RDFSAnnotation.IS_DEFINED_BY):
                prop_def.isDefinedBy = meta.value
            elif isinstance(meta, OWLAnnotation.EQUIVALENT_PROPERTY):
                prop_def.equivalentProperty = meta.value
            elif isinstance(meta, OWLAnnotation.INVERSE_OF):
                prop_def.inverseOf = meta.value
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
        for field_name, field_info in self._prop_db.items():
            prop_fields = dict()
            prop_fields["id"] = field_name
            if field_info["field_type"] == "Relation":
                prop_fields["type"] = ["owl:ObjectProperty"]
            else:
                prop_fields["type"] = ["owl:DatatypeProperty"]
                if (
                    field_info["field_type"] in self.type_map
                    and self.cfg.TYPE_AS_RDF_TYPE
                ):
                    prop_fields["type"].append(self.type_map[field_info["field_type"]])

            if self.cfg.FIELD_NAME_AS_LABEL:
                prop_fields["label"] = field_name

            if self.cfg.ORIGIN_AS_DOMAIN:
                if len(field_info["defined_in"]) > 1:
                    if self.cfg.SHOW_WARNINGS:
                        warnings.warn(
                            f"The 'ORIGIN_AS_DOMAIN' setting was ignored for '{field_name}' property since it is defined in multiple classes",
                            UserWarning,
                        )
                else:
                    prop_fields["domain"] = Relation(id=field_info["defined_in"][0])  # pyright: ignore
            if self.cfg.DESCRIPTION_AS_COMMENT:
                if len(field_info["description"]) > 1:
                    if self.cfg.SHOW_WARNINGS:
                        warnings.warn(
                            f"The 'DESCRIPTION_AS_COMMENT' setting was ignored for '{field_name}' property since it is defined in multiple classes",
                            UserWarning,
                        )
                else:
                    prop_fields["comment"] = field_info["description"][0]

            prop_def = _OntologyProperty.model_validate(prop_fields)
            if len(field_info["metadata"]) > 1:
                if self.cfg.SHOW_WARNINGS:
                    warnings.warn(
                        f"OWL/RDFS annotations will be concatenated for '{field_name}' property since it is defined in multiple classe",
                        UserWarning,
                    )
            self._add_property_annotations(
                prop_def, [m for sublist in field_info["metadata"] for m in sublist]
            )
            ontology_props.append(prop_def)
        return ontology_props

    def ontology_graph(
        self, context: BaseContext = BaseContext(), settings: Settings = Settings()
    ):
        """Generate ontology graph"""
        self.cfg = settings
        onto_classes = self._create_ontology_classes()
        onto_props = self._create_ontology_properties()
        return JSONLDGraph(context=context, graph=[*onto_classes, *onto_props])  # pyright: ignore

    def _add_shacl_annotations(
        self, prop_shape: _PropertyShape, annotations: List
    ) -> _PropertyShape:
        for meta in annotations:
            # Value Type Constraint Components
            if isinstance(meta, SHACLAnnotation.DATATYPE):
                prop_shape.datatype = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, SHACLAnnotation.CLASS):
                prop_shape.shclass = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, SHACLAnnotation.NODE_KIND):
                prop_shape.nodeKind = Relation(id=meta.value)  # pyright: ignore

            # Cardinality Constraint Components
            elif isinstance(meta, SHACLAnnotation.MAX_COUNT):
                prop_shape.maxCount = meta.value
            elif isinstance(meta, SHACLAnnotation.MIN_COUNT):
                prop_shape.minCount = meta.value

            # Value Range Constraint Components
            elif isinstance(meta, SHACLAnnotation.MIN_INCLUSIVE):
                prop_shape.minInclusive = meta.value
            elif isinstance(meta, SHACLAnnotation.MAX_INCLUSIVE):
                prop_shape.maxInclusive = meta.value
            elif isinstance(meta, SHACLAnnotation.MIN_EXCLUSIVE):
                prop_shape.minExclusive = meta.value
            elif isinstance(meta, SHACLAnnotation.MAX_EXCLUSIVE):
                prop_shape.maxExclusive = meta.value

            # String-based Constraint Components
            elif isinstance(meta, SHACLAnnotation.PATTERN):
                prop_shape.pattern = meta.value
            elif isinstance(meta, SHACLAnnotation.MIN_LENGTH):
                prop_shape.minLength = meta.value
            elif isinstance(meta, SHACLAnnotation.MAX_LENGTH):
                prop_shape.maxLength = meta.value
            elif isinstance(meta, SHACLAnnotation.LANGUAGE_IN):
                prop_shape.languageIn = meta.value
            elif isinstance(meta, SHACLAnnotation.UNIQUE_LANG):
                prop_shape.uniqueLang = meta.value

            # Property Pair Constraint Components
            elif isinstance(meta, SHACLAnnotation.EQUALS):
                prop_shape.equals = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, SHACLAnnotation.DISJOINT):
                prop_shape.disjoint = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, SHACLAnnotation.LESS_THAN):
                prop_shape.lessThan = Relation(id=meta.value)  # pyright: ignore
            elif isinstance(meta, SHACLAnnotation.LESS_THAN_OR_EQUALS):
                prop_shape.lessThanOrEquals = Relation(id=meta.value)  # pyright: ignore

            # Other Constraint Components
            elif isinstance(meta, SHACLAnnotation.CLOSED):
                prop_shape.closed = meta.value
            elif isinstance(meta, SHACLAnnotation.IGNORED_PROPERTIES):
                prop_shape.ignoredProperties = [
                    Relation(id=prop)  # pyright: ignore
                    for prop in meta.value
                ]
            elif isinstance(meta, SHACLAnnotation.HAS_VALUE):
                prop_shape.hasValue = meta.value
            # elif isinstance(meta, SHACLAnnotation.IN):
            #    prop_shape.shIn = meta.value

            # Validation parameter constructs
            elif isinstance(meta, SHACLAnnotation.SEVERITY):
                prop_shape.severity = Relation(id=meta.value)  # pyright: ignore

            # Non validating constructs
            elif isinstance(meta, SHACLAnnotation.NAME):
                prop_shape.name = meta.value
            elif isinstance(meta, SHACLAnnotation.DESCRIPTION):
                prop_shape.description = meta.value
        return prop_shape

    def _create_property_shapes(self, class_name: str) -> List[_PropertyShape]:
        """Create SHACL property shapes using _PropertyShape class"""

        prop_shapes = []

        for field_name, field_info in self._prop_db.items():
            # If field is (re)defined in class, get index into field_info for def
            if class_name not in field_info["defined_in"]:
                continue
            else:
                idx = field_info["defined_in"].index(class_name)

            prop_shape_fields = {
                "id": f"{class_name}Shape_{field_name}",
                "path": Relation(id=field_name),  # pyright: ignore
                "name": field_name if self.cfg.FIELD_NAME_AS_SH_NAME else None,
                "description": field_info["description"][idx]
                if self.cfg.DESCRIPTION_AS_SH_DESCRIPTION
                else None,
            }

            prop_shape = _PropertyShape.model_validate(prop_shape_fields)

            create_prop_shape = False
            if (
                field_info["field_type"] == "Relation"
                and self.cfg.RELATION_AS_NODEKIND_IRI
            ):
                prop_shape.nodeKind = Relation(id="sh:IRI")  # pyright: ignore
                create_prop_shape = True
            if (
                field_info["field_type"] in self.type_map
                and self.cfg.TYPE_AS_SH_DATATYPE
            ):
                prop_shape.datatype = Relation(
                    id=self.type_map[field_info["field_type"]]  # pyright: ignore
                )
                create_prop_shape = True

            # If no shacl annotations are in metadata and no default settings
            # imply a property shape is needed, then don't create property shape
            if (
                not any(
                    [
                        type(sh).__qualname__.startswith("SHACLAnnotation.")
                        for sh in field_info["metadata"][idx]
                    ]
                )
                and not create_prop_shape
            ):
                continue

            prop_shape = self._add_shacl_annotations(
                prop_shape, field_info["metadata"][idx]
            )
            prop_shapes.append(prop_shape)

        return prop_shapes

    def _create_node_shapes(self) -> List[_NodeShape]:
        node_shapes = []
        for class_name in self._cls_db.keys():
            property_shapes = self._create_property_shapes(class_name)

            # property_shapes is of lengt 0 if there are not SHACL annotations
            # in which case we continue
            if len(property_shapes) == 0:
                continue

            node_fields = {
                "id": f"{class_name}Shape",
                "targetClass": Relation(id=class_name),  # pyright: ignore
                "property": property_shapes,
            }

            node_shape = _NodeShape.model_validate(node_fields)
            node_shapes.append(node_shape)
        return node_shapes

    def shacl_graph(
        self, context: BaseContext = BaseContext(), settings: Settings = Settings()
    ):
        """Generate SHACL graph"""

        self.cfg = settings
        shacl_shapes = self._create_node_shapes()
        return JSONLDGraph(context=context, graph=shacl_shapes)  # pyright: ignore

    def _strip_type(self, tp: Any, cache: dict[type, type]) -> Any:
        origin = get_origin(tp)
        args = get_args(tp)

        # Basemodel
        if origin is None:
            if isinstance(tp, type) and issubclass(tp, BaseModel):
                return self._strip_model(tp, cache)
            return tp

        # Containers
        if origin in (list, set, tuple, frozenset):
            return origin[tuple(self._strip_type(a, cache) for a in args)]  # pyright: ignore

        # Dict
        if origin is dict:
            k, v = args
            return dict[self._strip_type(k, cache), self._strip_type(v, cache)]

        # Union (incl. | syntax)
        if origin is Union:
            return Union[tuple(self._strip_type(a, cache) for a in args)]

        return tp

    def _strip_aliases(self, tp: Any, cache: dict[type, type] | None = None) -> Any:
        """
        Returns an equivalent type with all Pydantic aliases removed.

        Accepts BaseModel, Union, or arbitrary nested type.
        """
        if cache is None:
            cache = {}
        return self._strip_type(tp, cache)

    def _strip_model(
        self, model: type[BaseModel], cache: dict[type, type]
    ) -> type[BaseModel]:
        if model in cache:
            return cache[model]

        new_fields = {}

        for name, field in model.model_fields.items():
            info: FieldInfo = deepcopy(field)

            # Remove alias-related metadata
            info.alias = None
            info.validation_alias = None
            info.serialization_alias = None

            new_type = self._strip_type(field.annotation, cache)

            if field.is_required():
                new_fields[name] = (new_type, info)
            else:
                new_fields[name] = (new_type, field.default)

        New = create_model(
            model.__name__,
            __base__=model,
            **new_fields,
        )

        cache[model] = New
        return New

    def schema_graph(self, context: BaseContext = BaseContext()) -> type[JSONLDGraph]:
        """
        Creates a JSONLDGraph subclass that holds ontology classes in the default graph.

        This class is specifically for LLM structured output, as it strips aliases
        from the ontology classes, which cause errors when using e.g. Pydantic AI.
        """
        return create_model(
            "PydontologySchema",
            context=(
                BaseContext,
                Field(
                    default=context,
                    json_schema_extra={
                        "name": "@context",
                        "description": "JSON-LD context",
                    },
                ),
            ),
            graph=(
                List[self._strip_aliases(self.ontology)],
                Field(
                    json_schema_extra={
                        "name": "@graph",
                        "description": "Default json-ld graph",
                    },
                ),
            ),
            __base__=JSONLDGraph,
        )

    def jsonld_graph(self, context: BaseContext = BaseContext()) -> type[JSONLDGraph]:
        return create_model(
            "PydontologyModel",
            context=(
                BaseContext,
                Field(
                    default=context,
                    json_schema_extra={
                        "name": "@context",
                        "description": "JSON-LD context",
                    },
                ),
            ),
            graph=(
                List[self.ontology],
                Field(
                    json_schema_extra={
                        "name": "@graph",
                        "description": "Default json-ld graph",
                    },
                ),
            ),
            __base__=JSONLDGraph,
        )
