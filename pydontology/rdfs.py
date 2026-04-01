from typing import Annotated

from pydantic import AfterValidator
from pydantic.dataclasses import dataclass

from .validators import val_no_whitespace


class RDFSAnnotation:
    """Provides methods for setting RDFS annotations.

    Encapsulates dataclasses that validate and provide type information for RDFS annotations.
    These annotations are used in the construction of the ontology graph.
    """

    @dataclass
    class DOMAIN:
        """Dataclass that holds rdfs:domain annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass
    class RANGE:
        """Dataclass that holds rdfs:range annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(unsafe_hash=True)
    class SUB_PROPERTY_OF:
        """Dataclass that holds rdfs:subPropertyOf annotation for a property"""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @staticmethod
    def domain(value: str) -> DOMAIN:
        """
        RDFS domain annotation.

        rdfs:domain is an instance of rdf:Property that is used to state that
        any resource that has a given property is an instance of one or more classes.

        Args:
            value (str): Name of RDFS class

        Returns:
            RDFSAnnotation.DOMAIN (dataclass)
        """
        return RDFSAnnotation.DOMAIN(value=value)

    @staticmethod
    def range(value: str) -> RANGE:
        """
        RDFS range annotation.

        rdfs:range is an instance of rdf:Property that is used to state
        that the values of a property are instances of one or more classes.

        Args:
            value (str): Name of RDFS class

        Returns:
            RDFSAnnotation.RANGE (dataclass)
        """
        return RDFSAnnotation.RANGE(value=value)

    @staticmethod
    def subPropertyOf(value: str) -> SUB_PROPERTY_OF:
        """
        RDFS subPropertyOf annotation.

        Relations described by subproperty also hold for superproperty.

        Args:
            value (str): Name of property

        Returns:
            RDFSAnnotation.SUB_PROPERTY_OF (dataclass)
        """
        return RDFSAnnotation.SUB_PROPERTY_OF(value=value)
