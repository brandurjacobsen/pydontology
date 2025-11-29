from typing import Annotated

from pydantic.dataclasses import dataclass
from pydantic.functional_validators import AfterValidator

from .validators import (
    val_datatype,
    val_no_whitespace,
    val_node_kind,
    val_non_negative_int,
    val_regex_pattern,
)


class SHACLAnnotation:
    """Provides methods for setting SHACL annotations.

    Encapsulates dataclasses that validate and provide type information for SHACL annotations.
    These annotations are used in the construction of the SHACL graph.
    """

    @dataclass
    class DATATYPE:
        """Dataclass that holds sh:datatype annotation for a property.

        The values of sh:datatype in a shape are IRIs (e.g. xsd:integer).
        A shape has at most one value for sh:datatype.

        Args:
            value (str): IRI of datatype
        """

        value: Annotated[str, AfterValidator(val_datatype)]

    @dataclass
    class MAX_COUNT:
        """Dataclass that holds sh:maxCount annotation for a property.

        The maximum cardinality.
        The values of sh:maxCount in a property shape are literals with datatype xsd:integer.

        Args:
            value (int): Max cardinality of property
        """

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass
    class MIN_COUNT:
        """Dataclass that holds sh:minCount annotation for a property.

        The minimum cardinality.
        The values of sh:minCount in a property shape are literals with datatype xsd:integer.

        Args:
            value (int): Min cardinality of property
        """

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass
    class PATTERN:
        """Dataclass that holds sh:pattern annotation for a property.

        String-based constraint.
        A regular expression that all value nodes need to match.
        The values of sh:pattern in a shape are valid pattern arguments for the SPARQL REGEX function.

        Args:
            value (str): SPARQL regex (validation not implemented!)
        """

        value: Annotated[str, AfterValidator(val_regex_pattern)]

    @dataclass
    class MIN_LENGTH:
        """Dataclass that holds sh:minLength annotation for a property.

        String-based constraint.
        The minimum length. The values of sh:minLength in a shape are literals with datatype xsd:integer.
        A shape has at most one value for sh:minLength.

        Args:
            value (int): Min length of RDF literal
        """

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass
    class MAX_LENGTH:
        """Dataclass that holds sh:maxLength annotation for a property.

        String-based constraint.
        The maximum length. The values of sh:maxLength in a shape are literals with datatype xsd:integer.
        A shape has at most one value for sh:maxLength.

        Args:
            value (int): Max length of RDF literal
        """

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass
    class MIN_INCLUSIVE:
        """Dataclass that holds sh:minInclusive annotation for a property.

        Value range constraint.
        The minimum inclusive value. The values of sh:minInclusive in a shape are literals.
        A shape has at most one value for sh:minInclusive.

        Args:
            value (int | float): Min inclusive value of RDF literal
        """

        value: int | float

    @dataclass
    class MAX_INCLUSIVE:
        """Dataclass that holds sh:maxInclusive annotation for a property.

        Value range constraint.
        The maximum inclusive value. The values of sh:maxInclusive in a shape are literals.
        A shape has at most one value for sh:maxInclusive.

        Args:
            value (int | float): Max inclusive value of RDF literal
        """

        value: int | float

    @dataclass
    class MIN_EXCLUSIVE:
        """Dataclass that holds sh:minExclusive annotation for a property.

        Value range constraint.
        The minimum exclusive value. The values of sh:minExclusive in a shape are literals.
        A shape has at most one value for sh:minExclusive.

        Args:
            value (int | float): Min exclusive value of RDF literal
        """

        value: int | float

    @dataclass
    class MAX_EXCLUSIVE:
        """Dataclass that holds sh:maxExclusive annotation for a property.

        Value range constraint.
        The maximum exclusive value. The values of sh:maxExclusive in a shape are literals.
        A shape has at most one value for sh:maxExclusive.

        Args:
            value (int | float): Max exclusive value of RDF literal
        """

        value: int | float

    @dataclass
    class NODE_KIND:
        """Dataclass that holds sh:nodeKind annotation for a property.

        Value type constraint.
        The values of sh:nodeKind in a shape are one of the following six instances of the class sh:NodeKind:
        sh:BlankNode, sh:IRI, sh:Literal sh:BlankNodeOrIRI, sh:BlankNodeOrLiteral and sh:IRIOrLiteral.
        A shape has at most one value for sh:nodeKind.

        Args:
            value (str): Instance of node kind
        """

        value: Annotated[str, AfterValidator(val_node_kind)]

    @dataclass
    class CLASS:
        """Dataclass that holds sh:class annotation for a property.

        Value type constraint.
        The type of all value nodes. The values of sh:class in a shape are IRIs.

        Args:
            value (str): IRI of class
        """

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @staticmethod
    def datatype(value: str) -> DATATYPE:
        """SHACLAnnotation.DATATYPE factory"""
        return SHACLAnnotation.DATATYPE(value)

    @staticmethod
    def maxCount(value: int) -> MAX_COUNT:
        """SHACLAnnotation.MAX_COUNT factory"""
        return SHACLAnnotation.MAX_COUNT(value)

    @staticmethod
    def minCount(value: int) -> MIN_COUNT:
        """SHACLAnnotation.MIN_COUNT factory"""
        return SHACLAnnotation.MIN_COUNT(value)

    @staticmethod
    def pattern(value: str) -> PATTERN:
        """SHACLAnnotation.PATTERN factory"""
        return SHACLAnnotation.PATTERN(value)

    @staticmethod
    def minLength(value: int) -> MIN_LENGTH:
        """SHACLAnnotation.MIN_LENGTH factory"""
        return SHACLAnnotation.MIN_LENGTH(value)

    @staticmethod
    def maxLength(value: int) -> MAX_LENGTH:
        """SHACLAnnotation.MAX_LENGTH factory"""
        return SHACLAnnotation.MAX_LENGTH(value)

    @staticmethod
    def minInclusive(value: float) -> MIN_INCLUSIVE:
        """SHACLAnnotation.MIN_INCLUSIVE factory"""
        return SHACLAnnotation.MIN_INCLUSIVE(value)

    @staticmethod
    def maxInclusive(value: float) -> MAX_INCLUSIVE:
        """SHACLAnnotation.MAX_INCLUSIVE factory"""
        return SHACLAnnotation.MAX_INCLUSIVE(value)

    @staticmethod
    def minExclusive(value: float) -> MIN_EXCLUSIVE:
        """SHACLAnnotation.MIN_EXCLUSIVE factory"""
        return SHACLAnnotation.MIN_EXCLUSIVE(value)

    @staticmethod
    def maxExclusive(value: float) -> MAX_EXCLUSIVE:
        """SHACLAnnotation.MAX_EXCLUSIVE factory"""
        return SHACLAnnotation.MAX_EXCLUSIVE(value)

    @staticmethod
    def nodeKind(value: str) -> NODE_KIND:
        """SHACLAnnotation.NODE_KIND factory"""
        return SHACLAnnotation.NODE_KIND(value)

    @staticmethod
    def shclass(value: str) -> CLASS:
        """SHACLAnnotation.CLASS factory"""
        return SHACLAnnotation.CLASS(value)
