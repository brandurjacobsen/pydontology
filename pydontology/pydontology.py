import json
import warnings
from copy import deepcopy
from inspect import get_annotations, isclass
from types import NoneType, UnionType
from typing import Annotated, Any, List, Literal, Optional, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, create_model
from pydantic.fields import FieldInfo

from .api import APIAnnotation
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
    "float": "xsd:decimal",
    "Decimal": "xsd:decimal",
    "bool": "xsd:boolean",
    "datetime": "xsd:dateTime",
    "date": "xsd:date",
}


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
            *TYPE_MAP.values(),
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
        if origin is Annotated:
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
                "class": cls,
            }

            # We use 'get_annotations' and not 'model_fields' because we only
            # want to process fields defined in the current class, not inherited fields
            for field_name in get_annotations(cls).keys():
                field_info = cls.model_fields[field_name]
                field_type = self._get_field_type(field_info)

                if self.cfg.TYPE_STRICT_MODE:
                    if field_type not in self.type_map and field_type != "Relation":
                        raise ValueError(
                            f"Field {field_name} has type {field_type} which is not a Relation, or in the type map (Setting: TYPE_STRICT_MODE)"
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
        """Resolve field type to one specific (optional) Python type as string or None"""
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

    def _normalize_api_base_path(self, base_path: str | None) -> str:
        if base_path is None:
            return ""
        base = base_path.strip()
        if base == "":
            return ""
        if not base.startswith("/"):
            base = f"/{base}"
        return base.rstrip("/")

    def _resolve_api_path(self, resource: str, path: str | None) -> str:
        if path is None:
            return f"/{resource}"
        if path.startswith("/"):
            return path
        return f"/{resource}/{path.lstrip('/')}"

    def _resolve_api_property_path(
        self, resource: str, property_name: str, path: str | None
    ) -> str:
        if path is None:
            return f"/{resource}/{property_name}"
        if path.startswith("/"):
            return path
        return f"/{resource}/{path.lstrip('/')}"

    def _collect_api_routes(self, metadata: List | None) -> List[APIAnnotation.ROUTE]:
        if not metadata:
            return []
        return [meta for meta in metadata if isinstance(meta, APIAnnotation.ROUTE)]

    def _unwrap_optional(self, tp: Any) -> Any:
        origin = get_origin(tp)
        if origin in (Union, UnionType):
            args = [arg for arg in get_args(tp) if arg is not NoneType]
            if len(args) == 1:
                return args[0]
        return tp

    def _is_list_type(self, tp: Any) -> bool:
        origin = get_origin(tp)
        return origin in (list, List)

    def _sparql_prefix_lines(
        self, base: str, vocab: str, extra: dict[str, str] | None
    ) -> str:
        prefixes: dict[str, str] = {":": vocab}
        if extra:
            prefixes.update(extra)

        lines = []
        for prefix, iri in sorted(prefixes.items()):
            prefix_key = prefix if prefix.endswith(":") else f"{prefix}:"
            lines.append(f"PREFIX {prefix_key} <{iri}>")

        if base:
            lines.append(f"BASE <{base}>")
        return "\n".join(lines)

    def _sparql_iri_for_id(self, base: str, identifier: str) -> str:
        if identifier.startswith("http://") or identifier.startswith("https://"):
            return f"<{identifier}>"
        return f"<{base}{identifier}>"

    def _sparql_construct_class_collection(self, cls_name: str) -> str:
        return (
            f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ ?s a :{cls_name} . ?s ?p ?o . }}"
        )

    def _sparql_construct_class_detail(self, cls_name: str, subject_iri: str) -> str:
        return (
            f"CONSTRUCT {{ {subject_iri} ?p ?o }} WHERE {{ {subject_iri} a :{cls_name} . {subject_iri} ?p ?o . }}"
        )

    def _sparql_construct_property_collection(
        self, cls_name: str, property_name: str
    ) -> str:
        return (
            f"CONSTRUCT {{ ?s :{property_name} ?o }} WHERE {{ ?s a :{cls_name} . ?s :{property_name} ?o . }}"
        )

    def _sparql_execute_construct(
        self,
        sparql_wrapper,
        query: str,
    ):
        sparql_wrapper.setQuery(query)
        result = sparql_wrapper.query().convert()
        if isinstance(result, bytes):
            return result.decode("utf-8")
        return result

    def _jsonld_to_entities(
        self, jsonld_data: dict | list, cls, vocab_iri: str
    ) -> list:
        if isinstance(jsonld_data, dict):
            graph = jsonld_data.get("@graph")
            if graph is None:
                graph = [jsonld_data]
        else:
            graph = jsonld_data

        entities = []
        expected_full = f"{vocab_iri}{cls.__name__}"
        for node in graph:
            node_type = node.get("@type")
            if node_type is None:
                continue
            if isinstance(node_type, list):
                if cls.__name__ not in node_type and expected_full not in node_type:
                    continue
            else:
                if node_type not in (cls.__name__, expected_full):
                    continue
            entities.append(cls.model_validate(self._normalize_jsonld_node(node)))
        return entities

    def _normalize_jsonld_node(self, node: dict) -> dict:
        normalized = {}
        for key, value in node.items():
            if isinstance(value, dict) and "@value" in value:
                normalized[key] = value["@value"]
            elif isinstance(value, list):
                normalized_list = []
                for item in value:
                    if isinstance(item, dict) and "@value" in item:
                        normalized_list.append(item["@value"])
                    else:
                        normalized_list.append(item)
                normalized[key] = normalized_list
            else:
                normalized[key] = value
        return normalized

    def _rdflib_object_to_value(self, term):
        from rdflib import Literal, URIRef

        if isinstance(term, Literal):
            return term.toPython()
        if isinstance(term, URIRef):
            return Relation(id=str(term))
        return None

    def generate_api(
        self,
        base_path: str | None = None,
        sparql_endpoint: str | None = None,
        sparql_user: str | None = None,
        sparql_password: str | None = None,
        sparql_headers: dict[str, str] | None = None,
        sparql_default_graph: str | None = None,
        sparql_timeout: int | None = None,
        sparql_prefixes: dict[str, str] | None = None,
        sparql_wrapper=None,
    ):
        """Generate a FastAPI app from API annotations."""

        try:
            from fastapi import Body, FastAPI, HTTPException
        except Exception as exc:
            raise ImportError(
                "FastAPI is required for generate_api(). Install with pydontology[api]."
            ) from exc

        api = FastAPI()
        base_prefix = self._normalize_api_base_path(base_path)
        write_methods = {"POST", "PUT", "PATCH"}

        use_sparql = sparql_wrapper is not None or sparql_endpoint is not None
        base_context = BaseContext()
        base_iri = base_context.base
        vocab_iri = base_context.vocab
        jsonld_context = base_context.model_dump(by_alias=True, exclude_none=True)
        prefix_lines = self._sparql_prefix_lines(base_iri, vocab_iri, sparql_prefixes)

        if use_sparql and sparql_wrapper is None:
            try:
                from SPARQLWrapper import SPARQLWrapper, XML
            except Exception as exc:
                raise ImportError(
                    "SPARQLWrapper is required for SPARQL-backed handlers. Install with pydontology[sparql]."
                ) from exc

            sparql_wrapper = SPARQLWrapper(sparql_endpoint)
            sparql_wrapper.setReturnFormat(XML)
            if sparql_user is not None:
                sparql_wrapper.setCredentials(sparql_user, sparql_password or "")
            if sparql_default_graph is not None:
                sparql_wrapper.addDefaultGraph(sparql_default_graph)
            if sparql_timeout is not None:
                sparql_wrapper.setTimeout(sparql_timeout)
            if sparql_headers:
                for header, value in sparql_headers.items():
                    sparql_wrapper.addCustomHttpHeader(header, value)

        def make_handler_no_body():
            def handler():
                raise HTTPException(501, "Not implemented")

            return handler

        def make_handler_with_body(body_type):
            def handler(payload: body_type = Body(...)):
                raise HTTPException(501, "Not implemented")

            return handler

        for class_name, class_info in self._cls_db.items():
            cls = class_info["class"]
            resource = class_name.lower()

            for route in self._collect_api_routes(class_info.get("metadata")):
                path = self._resolve_api_path(resource, route.path)
                if base_prefix:
                    path = f"{base_prefix}{path}"

                tags = route.tags if route.tags is not None else [class_name]
                request_model = cls if route.method in write_methods else None
                response_model = cls

                if route.method == "GET" and "{id}" not in path:
                    response_model = List[cls]
                if route.method == "DELETE":
                    response_model = None

                handler = None
                if use_sparql and route.method == "GET":

                    def handler(
                        id: str | None = None,
                        cls_name=class_name,
                        cls_type=cls,
                        route_path=path,
                    ):
                        from rdflib import Graph

                        subject_iri = None
                        query = None
                        if "{id}" in route_path:
                            if id is None:
                                raise HTTPException(422, "Missing id parameter")
                            subject_iri = self._sparql_iri_for_id(base_iri, id)
                            query = self._sparql_construct_class_detail(
                                cls_name, subject_iri
                            )
                        else:
                            query = self._sparql_construct_class_collection(cls_name)

                        full_query = f"{prefix_lines}\n{query}"
                        data = self._sparql_execute_construct(
                            sparql_wrapper, full_query
                        )

                        graph = Graph()
                        graph.parse(data=data, format="xml")
                        jsonld_text = graph.serialize(
                            format="json-ld",
                            auto_compact=True,
                            context=jsonld_context,
                        )
                        if isinstance(jsonld_text, bytes):
                            jsonld_text = jsonld_text.decode("utf-8")
                        jsonld = json.loads(jsonld_text)
                        entities = self._jsonld_to_entities(
                            jsonld, cls_type, vocab_iri
                        )

                        if "{id}" in route_path:
                            return entities[0] if entities else None
                        return entities

                if handler is None:
                    handler = (
                        make_handler_with_body(request_model)
                        if request_model is not None
                        else make_handler_no_body()
                    )

                api.api_route(
                    path,
                    methods=[route.method],
                    response_model=response_model,
                    tags=tags,
                )(handler)

            for field_name in get_annotations(cls).keys():
                field_info = cls.model_fields[field_name]
                field_routes = self._collect_api_routes(field_info.metadata)
                if not field_routes:
                    continue

                field_type = field_info.annotation or Any
                for route in field_routes:
                    path = self._resolve_api_property_path(
                        resource, field_name, route.path
                    )
                    if base_prefix:
                        path = f"{base_prefix}{path}"

                    tags = route.tags if route.tags is not None else [class_name]
                    request_model = field_type if route.method in write_methods else None
                    response_model = field_type

                    if route.method == "DELETE":
                        response_model = None

                    handler = None
                    if use_sparql and route.method == "GET":

                        def handler(
                            cls_name=class_name,
                            property_name=field_name,
                            field_tp=field_type,
                        ):
                            from rdflib import Graph

                            query = self._sparql_construct_property_collection(
                                cls_name, property_name
                            )
                            full_query = f"{prefix_lines}\n{query}"
                            data = self._sparql_execute_construct(
                                sparql_wrapper, full_query
                            )

                            from rdflib import URIRef

                            graph = Graph()
                            graph.parse(data=data, format="xml")
                            predicate = URIRef(f"{vocab_iri}{property_name}")
                            values = []
                            for _, _, obj in graph.triples((None, predicate, None)):
                                value = self._rdflib_object_to_value(obj)
                                if value is not None:
                                    values.append(value)

                            normalized_type = self._unwrap_optional(field_tp)
                            if self._is_list_type(normalized_type):
                                return values
                            return values[0] if values else None

                    if handler is None:
                        handler = (
                            make_handler_with_body(request_model)
                            if request_model is not None
                            else make_handler_no_body()
                        )

                    api.api_route(
                        path,
                        methods=[route.method],
                        response_model=response_model,
                        tags=tags,
                    )(handler)

        return api

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
            f"{model.__name__}NoAlias",
            __base__=model,
            **new_fields,
        )

        cache[model] = New
        return New

    def schema_graph(self, context: BaseContext = BaseContext()) -> type[JSONLDGraph]:
        """
        Makes a JSONLDGraph class from the ontology for making JSON schemas
        """
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
