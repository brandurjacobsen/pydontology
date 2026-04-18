from typing import Annotated

from pydantic import AfterValidator
from pydantic.dataclasses import dataclass

from .validators import val_no_whitespace


class OWLAnnotation:
    """Provides methods for setting OWL annotations.

    Encapsulates dataclasses that validate and provide type information for OWL annotations.
    These annotations are used in the construction of the ontology graph.
    """

    @dataclass(frozen=True)
    class EQUIVALENT_CLASS:
        """Dataclass that holds owl:equivalentClass annotation for a class"""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class SAME_AS:
        """Dataclass that holds owl:sameAs annotation for a class or instance of class"""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class EQUIVALENT_PROPERTY:
        """Dataclass that holds owl:equivalentProperty annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class INVERSE_OF:
        """Dataclass that holds owl:inverseOf annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

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
    def equivalentClass(value: str) -> EQUIVALENT_CLASS:
        """
        OWL equivalentClass annotation.

        owl:equivalentClass is used to state that two classes have the same class extension.

        Args:
            value (str): Name of the equivalent class

        Returns:
            OWLAnnotation.EQUIVALENT_CLASS (dataclass)
        """
        return OWLAnnotation.EQUIVALENT_CLASS(value=value)

    @staticmethod
    def sameAs(value: str) -> SAME_AS:
        """
        OWL sameAs annotation.

        owl:sameAs is used to state that two URI references refer to the same individual.

        Args:
            value (str): Name of the same individual

        Returns:
            OWLAnnotation.SAME_AS (dataclass)
        """
        return OWLAnnotation.SAME_AS(value=value)

    @staticmethod
    def equivalentProperty(value: str) -> EQUIVALENT_PROPERTY:
        """
        OWL equivalentProperty annotation.

        owl:equivalentProperty is used to state that two properties are equivalent.

        Args:
            value (str): Name of the equivalent property

        Returns:
            OWLAnnotation.EQUIVALENT_PROPERTY (dataclass)
        """
        return OWLAnnotation.EQUIVALENT_PROPERTY(value=value)

    @staticmethod
    def inverseOf(value: str) -> INVERSE_OF:
        """
        OWL inverseOf annotation.

        owl:inverseOf is used to state that one property is the inverse of another property.

        Args:
            value (str): Name of the inverse property

        Returns:
            OWLAnnotation.INVERSE_OF (dataclass)
        """
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
