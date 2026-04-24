from pydantic import HttpUrl
from pydantic.dataclasses import dataclass

from .models import Relation
from .owl import OWLAnnotation


class RDFSAnnotation:
    """Provides methods for setting RDFS annotations.

    Encapsulates dataclasses that validate and provide type information for RDFS annotations.
    These annotations are used in the construction of the ontology graph.
    """

    @dataclass(frozen=True)
    class DOMAIN:
        """Dataclass that holds rdfs:domain annotation for a property."""

        value: Relation

    @dataclass(frozen=True)
    class RANGE:
        """Dataclass that holds rdfs:range annotation for a property."""

        value: Relation

    @dataclass(frozen=True)
    class SUB_PROPERTY_OF:
        """Dataclass that holds rdfs:subPropertyOf annotation for a property"""

        value: Relation

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

        value: Relation | OWLAnnotation.Restriction

    @dataclass(frozen=True)
    class SEE_ALSO:
        """Dataclass that holds rdfs:seeAlso annotation for a class or property"""

        value: HttpUrl

    @dataclass(frozen=True)
    class IS_DEFINED_BY:
        """Dataclass that holds rdfs:isDefinedBy annotation for a class or property"""

        value: HttpUrl

    @staticmethod
    def domain(value: str | Relation) -> DOMAIN:
        """
        RDFS domain annotation.

        rdfs:domain is an instance of rdf:Property that is used to state that
        any resource that has a given property is an instance of one or more classes.

        Args:
            value (str | Relation): Ontology class name or Relation to ontology class

        Returns:
            RDFSAnnotation.DOMAIN (dataclass)
        """
        if isinstance(value, str):
            return RDFSAnnotation.DOMAIN(value=Relation(id=value))  # pyright: ignore
        return RDFSAnnotation.DOMAIN(value=value)  # pyright: ignore

    @staticmethod
    def range(value: str | Relation) -> RANGE:
        """
        RDFS range annotation.

        rdfs:range is an instance of rdf:Property that is used to state
        that the values of a property are instances of one or more classes.

        Args:
            value (str | Relation): Ontology class name or Relation to ontology class

        Returns:
            RDFSAnnotation.RANGE (dataclass)
        """
        if isinstance(value, str):
            return RDFSAnnotation.RANGE(value=Relation(id=value))  # pyright: ignore
        return RDFSAnnotation.RANGE(value=value)

    @staticmethod
    def subPropertyOf(value: str | Relation) -> SUB_PROPERTY_OF:
        """
        RDFS subPropertyOf annotation.

        rdfs:subPropertyOf is an instance of rdf:Property
        that states that the subject is a subproperty of a property (super-property).

        Args:
            value (str | Relation): Name of property or Relation to property

        Returns:
            RDFSAnnotation.SUB_PROPERTY_OF (dataclass)
        """
        if isinstance(value, str):
            return RDFSAnnotation.SUB_PROPERTY_OF(value=Relation(id=value))  # pyright: ignore
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
    def subClassOf(value: str | Relation | OWLAnnotation.Restriction) -> SUB_CLASS_OF:
        """
        RDFS subClassOf annotation.

        rdfs:subClassOf is an instance of rdf:Property that is used to state
        that all the instances of one class are instances of another.

        Args:
            value (str | Relation | Restriction): Name of parent class, Relation to parent class, or Restriction

        Returns:
            RDFSAnnotation.SUB_CLASS_OF (dataclass)
        """
        if isinstance(value, str):
            return RDFSAnnotation.SUB_CLASS_OF(value=Relation(id=value))  # pyright: ignore
        return RDFSAnnotation.SUB_CLASS_OF(value=value)

    @staticmethod
    def seeAlso(value: HttpUrl) -> SEE_ALSO:
        """
        RDFS seeAlso annotation.

        rdfs:seeAlso is an instance of rdf:Property that is used to indicate
        a resource that might provide additional information about the subject resource.

        Args:
            value (str): URL of related resource

        Returns:
            RDFSAnnotation.SEE_ALSO (dataclass)
        """
        return RDFSAnnotation.SEE_ALSO(value=value)

    @staticmethod
    def isDefinedBy(value: HttpUrl) -> IS_DEFINED_BY:
        """
        RDFS isDefinedBy annotation.

        rdfs:isDefinedBy is an instance of rdf:Property that is used to indicate
        a resource defining the subject resource.

        Args:
            value (str): URL of defining resource

        Returns:
            RDFSAnnotation.IS_DEFINED_BY (dataclass)
        """
        return RDFSAnnotation.IS_DEFINED_BY(value=value)
