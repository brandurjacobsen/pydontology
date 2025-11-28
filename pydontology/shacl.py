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
    """Helper class for SHACL annotations."""

    @dataclass
    class DATATYPE:
        """Metadata to specify sh:datatype for a property.

        The values of sh:datatype in a shape are IRIs (e.g. xsd:integer).
        A shape has at most one value for sh:datatype.
        """

        value: Annotated[str, AfterValidator(val_datatype)]

    @dataclass
    class MAX_COUNT:
        """Metadata to specify sh:maxCount for a property.

        The maximum cardinality.
        The values of sh:maxCount in a property shape are literals with datatype xsd:integer.
        """

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass
    class MIN_COUNT:
        """Metadata to specify sh:minCount for a property.

        The minimum cardinality.
        The values of sh:minCount in a property shape are literals with datatype xsd:integer.
        """

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass
    class PATTERN:
        """Metadata to specify sh:pattern for a property.

        A regular expression that all value nodes need to match.
        The values of sh:pattern in a shape are valid pattern arguments for the SPARQL REGEX function."""

        value: Annotated[str, AfterValidator(val_regex_pattern)]

    @dataclass
    class MIN_LENGTH:
        """Metadata to specify sh:minLength for a property.

        The minimum length. The values of sh:minLength in a shape are literals with datatype xsd:integer.
        A shape has at most one value for sh:minLength.
        """

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass
    class MAX_LENGTH:
        """Metadata to specify sh:maxLength for a property.

        The maximum length. The values of sh:maxLength in a shape are literals with datatype xsd:integer.
        A shape has at most one value for sh:maxLength.
        """

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass
    class MIN_INCLUSIVE:
        """Metadata to specify sh:minInclusive for a property.

        The minimum inclusive value. The values of sh:minInclusive in a shape are literals.
        A shape has at most one value for sh:minInclusive."""

        value: int | float

    @dataclass
    class MAX_INCLUSIVE:
        """Metadata to specify sh:maxInclusive for a property.

        The maximum inclusive value. The values of sh:maxInclusive in a shape are literals.
        A shape has at most one value for sh:maxInclusive.
        """

        value: int | float

    @dataclass
    class MIN_EXCLUSIVE:
        """Metadata to specify sh:minExclusive for a property.

        The minimum exclusive value. The values of sh:minExclusive in a shape are literals.
        A shape has at most one value for sh:minExclusive."""

        value: int | float

    @dataclass
    class MAX_EXCLUSIVE:
        """Metadata to specify sh:maxExclusive for a property.

        The maximum exclusive value. The values of sh:maxExclusive in a shape are literals.
        A shape has at most one value for sh:maxExclusive.
        """

        value: int | float

    @dataclass
    class NODE_KIND:
        """Metadata to specify sh:nodeKind for a property.

        The values of sh:nodeKind in a shape are one of the following six instances of the class sh:NodeKind:
        sh:BlankNode, sh:IRI, sh:Literal sh:BlankNodeOrIRI, sh:BlankNodeOrLiteral and sh:IRIOrLiteral.
        A shape has at most one value for sh:nodeKind.
        """

        value: Annotated[str, AfterValidator(val_node_kind)]

    @dataclass
    class CLASS:
        """Metadata to specify sh:class for a property.

        The type of all value nodes. The values of sh:class in a shape are IRIs.
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
