from typing import List, Literal, Optional, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.dataclasses import dataclass

from .models import RDFList, Relation


class OWLAnnotation:
    """Provides methods for setting OWL annotations.

    Encapsulates dataclasses that validate and provide type information for OWL annotations.
    These annotations are used in the construction of the ontology graph.
    """

    class Restriction(BaseModel):
        """Model for use in applying OWL restrictions"""

        type: Literal["owl:Restriction"] = Field(
            alias="@type", default="owl:Restriction"
        )
        onProperty: Relation = Field(alias="owl:onProperty")
        hasValue: Optional[str | Relation] = Field(alias="owl:hasValue", default=None)
        someValuesFrom: Optional[Relation] = Field(
            alias="owl:someValuesFrom", default=None
        )
        allValuesFrom: Optional[Relation] = Field(
            alias="owl:allValuesFrom", default=None
        )
        cardinality: Optional[int] = Field(alias="owl:cardinality", default=None)
        minCardinality: Optional[int] = Field(alias="owl:minCardinality", default=None)
        maxCardinality: Optional[int] = Field(alias="owl:maxCardinality", default=None)

        @model_validator(mode="after")
        def mutually_exclusive(self) -> Self:
            """Ensure only one restriction type is specified at a time."""
            restriction_fields = [
                "hasValue",
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

    @dataclass(frozen=True)
    class EQUIVALENT_CLASS:
        """Dataclass that holds owl:equivalentClass annotation for a class"""

        value: "Relation | OWLAnnotation.Restriction"

    @dataclass(frozen=True)
    class INTERSECTION_OF:
        """Dataclass that holds owl:intersectionOf annotation for a class"""

        value: RDFList

    @dataclass(frozen=True)
    class EQUIVALENT_PROPERTY:
        """Dataclass that holds owl:equivalentProperty annotation for a property."""

        value: Relation

    @dataclass(frozen=True)
    class INVERSE_OF:
        """Dataclass that holds owl:inverseOf annotation for a property."""

        value: Relation

    @dataclass(frozen=True)
    class TRANSITIVE_PROPERTY:
        """Dataclass that holds owl:TransitiveProperty annotation for a property."""

        value: bool = False

    @dataclass(frozen=True)
    class SYMMETRIC_PROPERTY:
        """Dataclass that holds owl:SymmetricProperty annotation for a property."""

        value: bool = False

    @dataclass(frozen=True)
    class FUNCTIONAL_PROPERTY:
        """Dataclass that holds owl:FunctionalProperty annotation for a property."""

        value: bool = False

    @dataclass(frozen=True)
    class INVERSE_FUNCTIONAL_PROPERTY:
        """Dataclass that holds owl:InverseFunctionalProperty annotation for a property."""

        value: bool = False

    @dataclass(frozen=True)
    class OBJECT_PROPERTY:
        """Dataclass that holds owl:ObjectProperty annotation for a property."""

        value: bool = False

    @dataclass(frozen=True)
    class DATATYPE_PROPERTY:
        """Dataclass that holds owl:DatatypeProperty annotation for a property."""

        value: bool = False

    @staticmethod
    def equivalentClass(value: str | Relation | Restriction) -> EQUIVALENT_CLASS:
        """
        OWL equivalentClass annotation.

        owl:equivalentClass is used to state that two classes have the same class extension.

        Args:
            value (str | Relation): Name of, Relation to the equivalent class, or Restriction

        Returns:
            OWLAnnotation.EQUIVALENT_CLASS (dataclass)
        """
        if isinstance(value, str):
            return OWLAnnotation.EQUIVALENT_CLASS(Relation(id=value))  # pyright: ignore
        return OWLAnnotation.EQUIVALENT_CLASS(value=value)

    @staticmethod
    def intersectionOf(
        value: List["str | Relation | OWLAnnotation.Restriction"],
    ) -> RDFList:
        """
        OWL intersectionOf annotation.

        owl:intersectionOf is used to state that the class consists of the intersection of individuals from named classes or Restrictions.

        Args:
            value (List[str | Relation | Restriction]) Construction of intersection

        Returns:
            OWLAnnotation.INTERSECTION_OF (dataclass)
        """

        lst = [Relation(id=item) if isinstance(item, str) else item for item in value]  # pyright: ignore
        return OWLAnnotation.INTERSECTION_OF(value=RDFList(list=lst))  # pyright: ignore

    @staticmethod
    def equivalentProperty(value: str | Relation) -> EQUIVALENT_PROPERTY:
        """
        OWL equivalentProperty annotation.

        owl:equivalentProperty is used to state that two properties are equivalent.

        Args:
            value (str): Name of the equivalent property

        Returns:
            OWLAnnotation.EQUIVALENT_PROPERTY (dataclass)
        """
        if isinstance(value, str):
            return OWLAnnotation.EQUIVALENT_PROPERTY(Relation(id=value))  # pyright: ignore
        return OWLAnnotation.EQUIVALENT_PROPERTY(value=value)

    @staticmethod
    def inverseOf(value: str | Relation) -> INVERSE_OF:
        """
        OWL inverseOf annotation.

        owl:inverseOf is used to state that one property is the inverse of another property.

        Args:
            value (str): Name of the inverse property

        Returns:
            OWLAnnotation.INVERSE_OF (dataclass)
        """
        if isinstance(value, str):
            return OWLAnnotation.INVERSE_OF(Relation(id=value))  # pyright: ignore
        return OWLAnnotation.INVERSE_OF(value=value)

    @staticmethod
    def transitiveProperty(value: bool) -> TRANSITIVE_PROPERTY:
        """
        OWL TransitiveProperty annotation.

        owl:TransitiveProperty is used to state that a property is transitive.
        If P is transitive, then for any x, y, z: P(x,y) and P(y,z) implies P(x,z).

        Args:
            value (bool): Whether the property is transitive

        Returns:
            OWLAnnotation.TRANSITIVE_PROPERTY (dataclass)
        """
        return OWLAnnotation.TRANSITIVE_PROPERTY(value=value)

    @staticmethod
    def symmetricProperty(value: bool) -> SYMMETRIC_PROPERTY:
        """
        OWL SymmetricProperty annotation.

        owl:SymmetricProperty is used to state that a property is symmetric.
        If P is symmetric, then for any x, y: P(x,y) implies P(y,x).

        Args:
            value (bool): Whether the property is symmetric

        Returns:
            OWLAnnotation.SYMMETRIC_PROPERTY (dataclass)
        """
        return OWLAnnotation.SYMMETRIC_PROPERTY(value=value)

    @staticmethod
    def functionalProperty(value: bool) -> FUNCTIONAL_PROPERTY:
        """
        OWL FunctionalProperty annotation.

        owl:FunctionalProperty is used to state that a property is functional.
        A functional property can have at most one value for each individual.

        Args:
            value (bool): Whether the property is functional

        Returns:
            OWLAnnotation.FUNCTIONAL_PROPERTY (dataclass)
        """
        return OWLAnnotation.FUNCTIONAL_PROPERTY(value=value)

    @staticmethod
    def inverseFunctionalProperty(value: bool) -> INVERSE_FUNCTIONAL_PROPERTY:
        """
        OWL InverseFunctionalProperty annotation.

        owl:InverseFunctionalProperty is used to state that a property is inverse functional.
        An inverse functional property can have at most one individual for each value.

        Args:
            value (bool): Whether the property is inverse functional

        Returns:
            OWLAnnotation.INVERSE_FUNCTIONAL_PROPERTY (dataclass)
        """
        return OWLAnnotation.INVERSE_FUNCTIONAL_PROPERTY(value=value)

    @staticmethod
    def objectProperty(value: bool) -> OBJECT_PROPERTY:
        """
        OWL ObjectProperty annotation.

        owl:ObjectProperty is used to state that a property relates individuals to individuals.

        Args:
            value (bool): Whether the property is an ObjectProperty

        Returns:
            OWLAnnotation.OBJECT_PROPERTY (dataclass)
        """
        return OWLAnnotation.OBJECT_PROPERTY(value=value)

    @staticmethod
    def datatypeProperty(value: bool) -> DATATYPE_PROPERTY:
        """
        OWL DatatypeProperty annotation.

        owl:DatatypeProperty is used to state that a property relates individuals to data values.

        Args:
            value (bool): Whether the property is a DatatypeProperty

        Returns:
            OWLAnnotation.DATATYPE_PROPERTY (dataclass)
        """
        return OWLAnnotation.DATATYPE_PROPERTY(value=value)
