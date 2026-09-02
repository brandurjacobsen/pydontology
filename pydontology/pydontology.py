import warnings
from copy import deepcopy
from inspect import get_annotations, isclass
from types import NoneType, UnionType
from typing import Annotated, Any, List, Union, get_args, get_origin

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

from .models import (
    BaseContext,
    BaseMetaData,
    Entity,
    JSONLDGraph,
    Relation,
    _NodeShape,
    _OntologyClass,
    _OntologyProperty,
    _PropertyShape,
)
from .owl import OWLAnnotation
from .rdfs import RDFSAnnotation
from .settings import Settings
from .shacl import SHACLAnnotation
from .types import TYPE_MAP, TYPE_SET

# _OntologyClass.model_rebuild()


class DuplicatePropertyError(Exception):
    """Raised when fields/properties are redefined erroneously"""


def _base_types(annotation) -> set | None:
    """Reduce an annotation to the set of concrete types it may hold.

    Recurses through unions (both typing.Union and PEP 604 'X | Y'), drops
    None/Optional members, and unwraps one level of container (list, List,
    set, frozenset, tuple). Returns None when the annotation cannot be reduced
    to concrete types (e.g. dict[str, int], or a union of several different
    container element types).
    """
    if annotation is None or annotation is NoneType:
        return set()
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        # Every union member must reduce to concrete types; the result is
        # their union. 'Optional[X]' is just 'X | None', so it reduces to X.
        result = set()
        for arg in get_args(annotation):
            part = _base_types(arg)
            if part is None:
                return None
            result |= part
        return result
    if origin in (list, set, frozenset, tuple):
        # Unwrap a single-element container, e.g. list[Relation] -> Relation.
        # Ellipsis is dropped to handle variable-length tuples (tuple[X, ...]).
        args = [a for a in get_args(annotation) if a is not Ellipsis]
        return _base_types(args[0]) if len(args) == 1 else None
    if origin is not None:
        return None  # some other generic alias, e.g. dict[str, int]
    # A plain type (builtin, Entity subclass, Relation, ...)
    return {annotation} if isinstance(annotation, type) else None


class Pydontology:
    type_map = TYPE_MAP

    def __init__(self, ontology: UnionType, metadata: BaseMetaData | None = None):
        self.ontology = ontology
        self.metadata = metadata

        # Get default settings for ontology_graph and shacl_graph methods
        self._apply_settings(Settings())

        # Construct a dict that maps Entity class names to class metadata
        self._cls_db = dict()

        # Construct a dict that maps field names/serializationaliases to field metadata
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
                    # field_type is a type object (or None); it must be Relation
                    # or a known literal type from the type map
                    if field_type is not Relation and field_type not in self.type_map:
                        raise ValueError(
                            f"Field '{field_name}' was resolved as type '{field_type}' which is not a Relation, nor in the type map (Setting: TYPE_STRICT_MODE)"
                        )

                # Fields are identified by serializationalias (if present), otherwise by name in the self._prop_db dict.
                # If an ontology class redefines a previously identified property (according to the above),
                # then the Python type needs to be identical, while e.g. default, description, title,
                # examples and SHACL annotation can vary.

                if field_info.serialization_alias is not None and field_info.serialization_alias in self._prop_db:
                    field_map = self._handle_duplicate_fields(
                        class_name, field_info.serialization_alias, field_type, field_info
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
                if field_info.serialization_alias is not None:
                    self._prop_db[field_info.serialization_alias] = field_map
                else:
                    self._prop_db[field_name] = field_map

    def _apply_settings(self, settings: Settings) -> None:
        """Apply Settings to runtime behavior, including Entity serialization."""
        self.cfg = settings
        # These flags control JSON-LD data serialization of Entity instances.
        Entity._serialize_literals_as_typeval = settings.LITERALS_AS_TYPEVAL
        Entity._type_strict_mode = settings.TYPE_STRICT_MODE

    def _get_field_type(self, field_info: FieldInfo):
        """Resolve a field annotation to a single concrete Python type.

        Returns the type object itself (callers compare by identity, e.g.
        `field_type is Relation`) or None when the annotation is ambiguous
        (a union of several different types) or unresolvable.
        Pydantic has already stripped Annotated metadata from
        field_info.annotation, so no Annotated handling is needed here.
        """
        types = _base_types(field_info.annotation)
        if types is None or len(types) != 1:
            return None
        return types.pop()

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

        # An explicit owl:ObjectProperty / owl:DatatypeProperty declaration
        # (last one wins) overrides the base type inferred from the field type.
        # Applied after the loop so property characteristics are preserved
        # regardless of annotation order.
        explicit_type = None
        for meta in annotations:
            if isinstance(meta, OWLAnnotation.OBJECT_PROPERTY) and meta.value:
                explicit_type = "owl:ObjectProperty"
            elif isinstance(meta, OWLAnnotation.DATATYPE_PROPERTY) and meta.value:
                explicit_type = "owl:DatatypeProperty"
        if explicit_type is not None:
            kept = [
                t
                for t in prop_def.type
                if t not in ("owl:ObjectProperty", "owl:DatatypeProperty")
            ]
            # An xsd rdf:type is only meaningful on a datatype property
            if explicit_type == "owl:ObjectProperty":
                kept = [t for t in kept if t not in TYPE_SET]
            prop_def.type = [explicit_type, *kept]

        return prop_def

    def _create_ontology_properties(self) -> List[_OntologyProperty]:
        """Create ontology properties using _OntologyProperty class"""
        ontology_props = []
        for field_name, field_info in self._prop_db.items():
            prop_fields = dict()
            prop_fields["id"] = field_name
            # field_type is a type object; identity-check against Relation
            if field_info["field_type"] is Relation:
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
                        f"OWL/RDFS annotations will be concatenated/added for '{field_name}' property since it is defined in multiple classe",
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
        self._apply_settings(settings)

        onto_classes = self._create_ontology_classes()
        onto_props = self._create_ontology_properties()
        graph = [*onto_classes, *onto_props]

        if self.metadata is not None:
            graph.append(self.metadata)

        return JSONLDGraph(
            context=context,  # pyright: ignore
            graph=graph,  # pyright: ignore
        )

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
                prop_shape.languageIn = list(meta.value)
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
            # (SHACLAnnotation.CLOSED / IGNORED_PROPERTIES are node-shape
            # constructs handled in _add_node_shape_annotations)
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
                field_info["field_type"] is Relation
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
            # imply a property shape is needed, then don't create property shape.
            # CLOSED/IGNORED_PROPERTIES are node-shape constructs and must not
            # trigger creation of a (nearly empty) property shape.
            if (
                not any(
                    [
                        type(sh).__qualname__.startswith("SHACLAnnotation.")
                        and not isinstance(
                            sh,
                            (SHACLAnnotation.CLOSED, SHACLAnnotation.IGNORED_PROPERTIES),
                        )
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

    def _add_node_shape_annotations(
        self, node_shape: _NodeShape, annotations: List
    ) -> _NodeShape:
        """Apply class-level SHACL annotations (node-shape constructs) to a node shape.

        E.g. Annotated[MyClass, SH.closed(True)]
        """
        for meta in annotations:
            if isinstance(meta, SHACLAnnotation.CLOSED):
                node_shape.closed = meta.value
            elif isinstance(meta, SHACLAnnotation.IGNORED_PROPERTIES):
                node_shape.ignoredProperties = [
                    Relation(id=prop) for prop in meta.value
                ]
        return node_shape

    def _create_node_shapes(self) -> List[_NodeShape]:
        node_shapes = []
        for class_name, class_info in self._cls_db.items():
            property_shapes = self._create_property_shapes(class_name)
            class_metadata = class_info["metadata"] or []

            # sh:closed / sh:ignoredProperties are node-shape constructs given
            # as class-level annotations; a node shape is needed for them even
            # if the class has no property shapes
            has_node_annotations = any(
                isinstance(
                    m, (SHACLAnnotation.CLOSED, SHACLAnnotation.IGNORED_PROPERTIES)
                )
                for m in class_metadata
            )

            # No property shapes and no node-shape annotations -> no node shape
            if len(property_shapes) == 0 and not has_node_annotations:
                continue

            node_fields = {
                "id": f"{class_name}Shape",
                "targetClass": Relation(id=class_name),  # pyright: ignore
                "property": property_shapes,
            }

            node_shape = _NodeShape.model_validate(node_fields)
            node_shape = self._add_node_shape_annotations(node_shape, class_metadata)
            node_shapes.append(node_shape)
        return node_shapes

    def shacl_graph(
        self, context: BaseContext = BaseContext(), settings: Settings = Settings()
    ):
        """Generate SHACL graph"""
        self._apply_settings(settings)
        shacl_shapes = self._create_node_shapes()
        return JSONLDGraph(context=context, graph=shacl_shapes)  # pyright: ignore


    def jsonld_graph(
        self,
        name: str = "PydontologyModel",
        context: BaseContext = BaseContext(),
        settings: Settings = Settings(),
    ) -> type[JSONLDGraph]:
        self._apply_settings(settings)
        return create_model(
            name,
            context=(
                BaseContext,
                Field(
                    serialization_alias="@context",
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
                    serialization_alias="@graph",
                    json_schema_extra={
                        "name": "@graph",
                        "description": "Default json-ld graph",
                    },
                ),
            ),
            __base__=JSONLDGraph,
        )

    def schema_graph(
        self,
        name: str = "PydontologyModel",
        context: BaseContext = BaseContext(),
        settings: Settings = Settings(),
    ) -> type[JSONLDGraph]:
        """Backward-compatible alias for jsonld_graph() (pre-rename name)."""
        return self.jsonld_graph(name=name, context=context, settings=settings)
