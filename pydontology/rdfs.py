from typing import Annotated

from pydantic import AfterValidator, HttpUrl
from pydantic.dataclasses import dataclass

from .validators import val_no_whitespace


class RDFSAnnotation:
    """Provides methods for setting RDFS annotations.

    Encapsulates dataclasses that validate and provide type information for RDFS annotations.
    These annotations are used in the construction of the ontology graph.
    """

    @dataclass(frozen=True)
    class DOMAIN:
        """Dataclass that holds rdfs:domain annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class RANGE:
        """Dataclass that holds rdfs:range annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class SUB_PROPERTY_OF:
        """Dataclass that holds rdfs:subPropertyOf annotation for a property"""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class COMMENT:
        """Dataclass that holds rdfs:comment annotation for a class or property."""

        value: str

    @dataclass(frozen=True)
    class LABEL:
        """Dataclass that holds rdfs:label annotation for a class or property."""

        value: str

    @dataclass(frozen=True)
    class SUB_CLASS_OF:
        """Dataclass that holds rdfs:subClassOf annotation for a class."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class SEE_ALSO:
        """Dataclass that holds rdfs:seeAlso annotation for a class or property"""

        value: HttpUrl

    @dataclass(frozen=True)
    class IS_DEFINED_BY:
        """Dataclass that holds rdfs:isDefinedBy annotation for a class or property"""

        value: HttpUrl

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

    @staticmethod
    def comment(value: str) -> COMMENT:
        """
        RDFS comment annotation.

        rdfs:comment is an instance of rdf:Property that may be used to provide
        a human-readable description of a resource.

        Args:
            value (str): Comment text

        Returns:
            RDFSAnnotation.COMMENT (dataclass)
        """
        return RDFSAnnotation.COMMENT(value=value)

    @staticmethod
    def label(value: str) -> LABEL:
        """
        RDFS label annotation.

        rdfs:label is an instance of rdf:Property that may be used to provide
        a human-readable version of a resource's name.

        Args:
            value (str): Label text

        Returns:
            RDFSAnnotation.LABEL (dataclass)
        """
        return RDFSAnnotation.LABEL(value=value)

    @staticmethod
    def subClassOf(value: str) -> SUB_CLASS_OF:
        """
        RDFS subClassOf annotation.

        rdfs:subClassOf is an instance of rdf:Property that is used to state
        that all the instances of one class are instances of another.

        Args:
            value (str): Name of parent class

        Returns:
            RDFSAnnotation.SUB_CLASS_OF (dataclass)
        """
        return RDFSAnnotation.SUB_CLASS_OF(value=value)

    # add methods for rdfs:seeAlso and rdfs:isDefinedBy constructs AI!
