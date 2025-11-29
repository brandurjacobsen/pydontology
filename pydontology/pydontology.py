from types import UnionType
from typing import Annotated, List, Literal, Optional, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, computed_field, create_model
from pydantic.json_schema import SkipJsonSchema

from .rdfs import RDFSAnnotation
from .shacl import SHACLAnnotation


class Relation(BaseModel):
    """This class should be the type of Entity attributes to be considered as IRIs.

    Args:
        id (str): IRI of relation
    """

    id: str = Field(alias="@id", title="@id", description="IRI (possibly relative)")
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class Entity(BaseModel):
    """The base class of all ontology classes.

    Args:
        id (str): IRI
    """

    id: str = Field(alias="@id", description="IRI (possibly relative)", title="@id")

    @computed_field(alias="@type", title="@type", description="JSON-LD @type")
    @property
    def type(self) -> str:
        return type(self).__name__

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class OntologyClass(BaseModel):
    """Represents an RDFS/OWL class in an ontology."""

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


class OntologyProperty(BaseModel):
    """Represents an OWL property in an ontology."""

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


class PropertyShape(BaseModel):
    """Represents a SHACL property shape."""

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


class NodeShape(BaseModel):
    """Represents a SHACL node shape."""

    id: str = Field(alias="@id", description="Node shape IRI")
    type: Literal["sh:NodeShape"] = Field(default="sh:NodeShape", alias="@type")
    targetClass: Relation = Field(alias="sh:targetClass", description="Target class")
    property: List[PropertyShape] = Field(
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
    """Encapsulates a JSON-LD document/graph.

    This is the return type of the make_model() function, and
    ontology_graph(), shacl_graph() class methods.
    """

    context: SkipJsonSchema[dict] = Field(
        default={
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/",
        },
        alias="@context",
        title="@context",
        description="JSON-LD context",
    )

    graph: List = Field(
        default=[], alias="@graph", title="@graph", description="Default graph"
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    @classmethod
    def ontology_graph(cls) -> "JSONLDGraph":
        """Generate an ontology graph from the classes in the ontology.

        Returns:
            JSONLDGraph: With RDFS/OWL class and property definitions.
        """

        # Collect unique entity types from the model
        entity_classes = cls._collect_entity_classes_from_model()

        # Generate class and property definitions
        ontology_entities: List[OntologyClass | OntologyProperty] = []
        properties_seen = set()

        for entity_class in entity_classes:
            # Add class definition
            class_def = cls._create_class_definition(entity_class, entity_classes)
            ontology_entities.append(class_def)

            # Add property definitions
            property_defs = cls._create_property_definitions(
                entity_class, properties_seen
            )
            ontology_entities.extend(property_defs)

        # Extract vocab from context
        vocab = cls.model_fields["context"].default.get(
            "@vocab", "http://example.com/vocab/"
        )

        # Build ontology context
        ontology_context = {
            "@vocab": vocab,
            "@base": vocab,
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
        }

        # Return as JSONLDGraph
        return JSONLDGraph(context=ontology_context, graph=ontology_entities)

    @classmethod
    def shacl_graph(cls) -> "JSONLDGraph":
        """Generate SHACL shapes graph from the classes in the ontology.

        Returns:
            JSONLDGraph: With SHACL NodeShape and PropertyShape definitions.
        """

        # Collect unique entity types from the model
        entity_classes = cls._collect_entity_classes_from_model()

        # Generate node shapes
        shacl_shapes: List[NodeShape] = []

        for entity_class in entity_classes:
            # Create node shape for this class
            node_shape = cls._create_node_shape(entity_class)
            shacl_shapes.append(node_shape)

        # Extract vocab from context
        vocab = cls.model_fields["context"].default.get(
            "@vocab", "http://example.com/vocab/"
        )

        # Build SHACL context
        shacl_context = {
            "@vocab": vocab,
            "@base": vocab,
            "sh": "http://www.w3.org/ns/shacl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        }

        # Return as JSONLDGraph
        return JSONLDGraph(context=shacl_context, graph=shacl_shapes)

    @classmethod
    def _collect_entity_classes_from_model(cls) -> set:
        """Collect all Entity classes from the model's graph field type annotation.

        Returns:
            set: All Entity classes found in the model's graph field annotation.
        """
        entity_classes = set()

        # Get the graph field's annotation
        graph_field = cls.model_fields.get("graph")
        if graph_field and graph_field.annotation:
            annotation = graph_field.annotation

            # Extract the entity type from List[EntityType] or List[A|B|C]
            origin = get_origin(annotation)
            if origin is list or origin is List:
                args = get_args(annotation)
                if args:
                    inner_type = args[0]

                    # Check if inner type is a Union (A|B|C or Union[A, B, C])
                    inner_origin = get_origin(inner_type)
                    # Handle both Union[A, B, C] and A|B|C (UnionType in Python 3.10+)
                    if inner_origin is Union or isinstance(inner_type, UnionType):
                        # Handle List[A|B|C] - extract all union members
                        union_args = get_args(inner_type)
                        for entity_type in union_args:
                            if isinstance(entity_type, type) and issubclass(
                                entity_type, Entity
                            ):
                                entity_classes.add(entity_type)
                                entity_classes.update(
                                    cls._get_all_subclasses(entity_type)
                                )
                    else:
                        # Handle List[EntityType] - single entity type
                        if isinstance(inner_type, type) and issubclass(
                            inner_type, Entity
                        ):
                            entity_classes.add(inner_type)
                            entity_classes.update(cls._get_all_subclasses(inner_type))

        return entity_classes

    @classmethod
    def _get_all_subclasses(cls, entity_class) -> set:
        """Recursively get all subclasses of an entity class.

        Args:
            entity_class: The entity class to find subclasses for.

        Returns:
            set: All subclasses of the given entity class.
        """
        subclasses = set()
        for subclass in entity_class.__subclasses__():
            subclasses.add(subclass)
            subclasses.update(cls._get_all_subclasses(subclass))
        return subclasses

    @classmethod
    def _create_class_definition(
        cls, entity_class, entity_classes: set
    ) -> OntologyClass:
        """Create an RDFS class definition for an Entity class.

        Args:
            entity_class: The Entity class to create a definition for.
            entity_classes: Set of all entity classes in the model.

        Returns:
            OntologyClass: RDFS class definition.
        """
        class_def = OntologyClass(
            id=entity_class.__name__,
            label=entity_class.__name__,
            comment=entity_class.__doc__.strip() if entity_class.__doc__ else None,
        )

        # Add inheritance relationships
        for base in entity_class.__bases__:
            if base != Entity and issubclass(base, Entity):
                class_def.subClassOf = Relation(id=base.__name__)
                entity_classes.add(base)

        return class_def

    @classmethod
    def _create_property_definitions(
        cls, entity_class, properties_seen: set
    ) -> List[OntologyProperty]:
        """Create property definitions for fields defined on a class.

        Args:
            entity_class: The Entity class to create property definitions for.
            properties_seen: Set of property names already processed.

        Returns:
            List[OntologyProperty]: Property definitions for the class fields.
        """
        property_defs = []
        parent_fields = cls._get_parent_fields(entity_class)

        for field_name, field_info in entity_class.model_fields.items():
            # Skip special fields and inherited fields
            if field_name in ["id", "type"] or field_name in parent_fields:
                continue

            # Skip duplicates
            if field_name in properties_seen:
                continue
            properties_seen.add(field_name)

            # Create property definition
            prop_def = cls._create_single_property_definition(
                entity_class, field_name, field_info, field_name
            )
            property_defs.append(prop_def)

        return property_defs

    @classmethod
    def _get_parent_fields(cls, entity_class) -> set:
        """Get all field names from parent classes.

        Args:
            entity_class: The Entity class to get parent fields for.

        Returns:
            set: Field names from all parent classes.
        """
        parent_fields = set()
        for base in entity_class.__bases__:
            if base != Entity and issubclass(base, Entity):
                parent_fields.update(base.model_fields.keys())
        return parent_fields

    @classmethod
    def _create_single_property_definition(
        cls, entity_class, field_name: str, field_info, prop_name: str
    ) -> OntologyProperty:
        """Create a single property definition.

        Args:
            entity_class: The Entity class containing the field.
            field_name: Name of the field.
            field_info: Pydantic field information.
            prop_name: Name for the property.

        Returns:
            OntologyProperty: Property definition for the field.
        """
        # Extract type and metadata
        field_type, metadata = cls._extract_field_type_and_metadata(
            entity_class, field_name, field_info
        )

        # Determine if ObjectProperty or DatatypeProperty
        is_relation = cls._is_relation_type(field_type)

        prop_def = OntologyProperty(
            id=prop_name,
            type="owl:ObjectProperty" if is_relation else "owl:DatatypeProperty",
            label=prop_name,
            domain=Relation(id=entity_class.__name__),
            comment=field_info.description,
        )

        # Add properties to OntologyProperty according to annotation
        for meta in metadata:
            if isinstance(meta, RDFSAnnotation.DOMAIN):
                prop_def.domain = Relation(id=meta.value)
            if isinstance(meta, RDFSAnnotation.RANGE):
                prop_def.range = Relation(id=meta.value)

        return prop_def

    @classmethod
    def _create_node_shape(cls, entity_class) -> NodeShape:
        """Create a SHACL node shape for an Entity class.

        Args:
            entity_class: The Entity class to create a node shape for.

        Returns:
            NodeShape: SHACL node shape for the entity class.
        """
        # Create property shapes for all fields
        property_shapes = []

        for field_name, field_info in entity_class.model_fields.items():
            # Skip special fields
            if field_name in ["id", "type"]:
                continue

            # Create property shape
            prop_shape = cls._create_property_shape(
                entity_class, field_name, field_info
            )
            property_shapes.append(prop_shape)

        # Create node shape
        node_shape = NodeShape(
            id=f"{entity_class.__name__}Shape",
            targetClass=Relation(id=entity_class.__name__),
            property=property_shapes,
        )

        return node_shape

    @classmethod
    def _create_property_shape(
        cls, entity_class, field_name: str, field_info
    ) -> PropertyShape:
        """Create a SHACL property shape for a field.

        Args:
            entity_class: The Entity class containing the field.
            field_name: Name of the field.
            field_info: Pydantic field information.

        Returns:
            PropertyShape: SHACL property shape for the field.
        """
        # Extract type and metadata
        field_type, metadata = cls._extract_field_type_and_metadata(
            entity_class, field_name, field_info
        )

        # Determine if this is a relation
        is_relation = cls._is_relation_type(field_type)

        # Create base property shape
        prop_shape = PropertyShape(
            id=f"{entity_class.__name__}Shape_{field_name}",
            path=Relation(id=field_name),
            name=field_name,
            description=field_info.description,
        )

        # Map Python types to XSD datatypes
        datatype_map = {
            str: "xsd:string",
            int: "xsd:integer",
            float: "xsd:decimal",
            bool: "xsd:boolean",
        }

        # Set datatype or class based on field type
        if is_relation:
            prop_shape.nodeKind = Relation(id="sh:IRI")
        else:
            if field_type in datatype_map:
                prop_shape.datatype = Relation(id=datatype_map[field_type])

        # Check if field is required (not Optional)
        if not field_info.is_required():
            # Optional field - no minCount constraint
            pass
        else:
            # Required field has minCount constraint
            prop_shape.minCount = 1

        # Apply SHACL annotations from metadata
        for meta in metadata:
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

        return prop_shape

    @classmethod
    def _extract_field_type_and_metadata(
        cls, entity_class, field_name: str, field_info
    ) -> tuple:
        """Extract the field type and metadata from annotations.

        Args:
            entity_class: The Entity class containing the field.
            field_name: Name of the field.
            field_info: Pydantic field information.

        Returns:
            tuple: Field type and metadata tuple.
        """
        field_type = field_info.annotation
        metadata = ()

        # Get original annotation
        original_annotation = None
        if (
            hasattr(entity_class, "__annotations__")
            and field_name in entity_class.__annotations__
        ):
            original_annotation = entity_class.__annotations__[field_name]

        # Extract metadata from Annotated
        if original_annotation and get_origin(original_annotation) is Annotated:
            args = get_args(original_annotation)
            field_type = args[0]
            metadata = args[1:]

        # Handle Optional types
        origin = getattr(field_type, "__origin__", None)
        if origin is not None:
            args = getattr(field_type, "__args__", ())
            if args:
                field_type = args[0]

        return field_type, metadata

    @classmethod
    def _is_relation_type(cls, field_type) -> bool:
        """Check if a field type is a Relation (ObjectProperty).

        Args:
            field_type: The field type to check.

        Returns:
            bool: True if the field type is a Relation, False otherwise.
        """
        try:
            if isinstance(field_type, type) and issubclass(field_type, Relation):
                return True
        except TypeError:
            pass
        return False


def make_model(ontology: type[Entity], name: str = "Pydontology") -> type[JSONLDGraph]:
    """Create a JSONLDGraph Pydantic model class

    Args:
        ontology (Union): Entity type or union of Entity types for the ontology.
        name (str): Name for the generated model class.

    Returns:
        type[JSONLDGraph]: A Pydantic model class with the specified ontology.

    Example::

        from pydontology import Entity, make_model

        class Person(Entity):
            name: str

        class Employee(Person):
            title: str

        ontology = Person | Employee
        Model = make_model(ontology)
    """

    return create_model(
        f"{name}",
        graph=(
            List[ontology],
            Field(
                alias="@graph",
                json_schema_extra={"name": "@graph", "description": "Default graph"},
            ),
        ),
        __base__=JSONLDGraph,
    )
