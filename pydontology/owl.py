from typing import Annotated

from pydantic import AfterValidator
from pydantic.dataclasses import dataclass

from .validators import val_no_whitespace


class OWLAnnotation:
    """Provides methods for setting OWL annotations.

    Encapsulates dataclasses that validate and provide type information for OWL annotations.
    These annotations are used in the construction of the ontology graph.
    """

    @dataclass
    class INVERSE_OF:
        """Dataclass that holds owl:inverseOf annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass
    class TRANSITIVE_PROPERTY:
        """Dataclass that holds owl:TransitiveProperty annotation for a property."""

        value: bool = False

    @dataclass
    class SYMMETRIC_PROPERTY:
        """Dataclass that holds owl:SymmetricProperty annotation for a property."""

        value: bool = False

    @dataclass
    class FUNCTIONAL_PROPERTY:
        """Dataclass that holds owl:FunctionalProperty annotation for a property."""

        value: bool = False

    @dataclass
    class INVERSE_FUNCTIONAL_PROPERTY:
        """Dataclass that holds owl:InverseFunctionalProperty annotation for a property."""

        value: bool = False

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

        Returns:
            OWLAnnotation.INVERSE_FUNCTIONAL_PROPERTY (dataclass)
        """
        return OWLAnnotation.INVERSE_FUNCTIONAL_PROPERTY(value=value)
