from typing import Annotated

from pydantic.dataclasses import dataclass
from pydantic.functional_validators import AfterValidator

from .validators import (
    val_datatype,
    val_no_whitespace,
    val_node_kind,
    val_non_negative_int,
    val_regex_pattern,
    val_severity_cls,
)


class SHACLAnnotation:
    """Provides methods for setting SHACL annotations.

    Encapsulates dataclasses that validate and provide type information for SHACL annotations.
    These annotations are used in the construction of the SHACL graph.
    """

    @dataclass(frozen=True)
    class DATATYPE:
        """Dataclass that holds sh:datatype annotation for a property."""

        value: Annotated[str, AfterValidator(val_datatype)]

    @dataclass(frozen=True)
    class MAX_COUNT:
        """Dataclass that holds sh:maxCount annotation for a property."""

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass(frozen=True)
    class MIN_COUNT:
        """Dataclass that holds sh:minCount annotation for a property."""

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass(frozen=True)
    class PATTERN:
        """Dataclass that holds sh:pattern annotation for a property."""

        value: Annotated[str, AfterValidator(val_regex_pattern)]

    @dataclass(frozen=True)
    class MIN_LENGTH:
        """Dataclass that holds sh:minLength annotation for a property."""

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass(frozen=True)
    class MAX_LENGTH:
        """Dataclass that holds sh:maxLength annotation for a property."""

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass(frozen=True)
    class MIN_INCLUSIVE:
        """Dataclass that holds sh:minInclusive annotation for a property."""

        value: int | float

    @dataclass(frozen=True)
    class MAX_INCLUSIVE:
        """Dataclass that holds sh:maxInclusive annotation for a property."""

        value: int | float

    @dataclass(frozen=True)
    class MIN_EXCLUSIVE:
        """Dataclass that holds sh:minExclusive annotation for a property."""

        value: int | float

    @dataclass(frozen=True)
    class MAX_EXCLUSIVE:
        """Dataclass that holds sh:maxExclusive annotation for a property."""

        value: int | float

    @dataclass(frozen=True)
    class NODE_KIND:
        """Dataclass that holds sh:nodeKind annotation for a property."""

        value: Annotated[str, AfterValidator(val_node_kind)]

    @dataclass(frozen=True)
    class CLASS:
        """Dataclass that holds sh:class annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class SEVERITY:
        """Dataclass that holds sh:severity annotation for a property"""

        value: Annotated[str, AfterValidator(val_severity_cls)]

    @staticmethod
    def datatype(value: str) -> DATATYPE:
        """SHACL datatype annotation.

        The values of sh:datatype in a shape are IRIs (e.g. xsd:integer).
        A shape has at most one value for sh:datatype.

        Args:
            value (str): IRI of datatype

        Returns:
            SHACLAnnotation.DATATYPE (dataclass)
        """
        return SHACLAnnotation.DATATYPE(value)

    @staticmethod
    def maxCount(value: int) -> MAX_COUNT:
        """SHACL maxCount annotation.

        The maximum cardinality.
        The values of sh:maxCount in a property shape are literals with datatype xsd:integer.

        Args:
            value (int): Max cardinality of property

        Returns:
            SHACLAnnotation.MAX_COUNT (dataclass)
        """
        return SHACLAnnotation.MAX_COUNT(value)

    @staticmethod
    def minCount(value: int) -> MIN_COUNT:
        """SHACL minCount annotation.

        The minimum cardinality.
        The values of sh:minCount in a property shape are literals with datatype xsd:integer.

        Args:
            value (int): Min cardinality of property

        Returns:
            SHACLAnnotation.MIN_COUNT (dataclass)
        """
        return SHACLAnnotation.MIN_COUNT(value)

    @staticmethod
    def pattern(value: str) -> PATTERN:
        """SHACL pattern annotation.

        String-based constraint.
        A regular expression that all value nodes need to match.
        The values of sh:pattern in a shape are valid pattern arguments for the SPARQL REGEX function.

        Args:
            value (str): SPARQL regex (validation not implemented!)

        Returns:
            SHACLAnnotation.PATTERN (dataclass)
        """
        return SHACLAnnotation.PATTERN(value)

    @staticmethod
    def minLength(value: int) -> MIN_LENGTH:
        """SHACL minLength annotation.

        The minimum length of an RDF literal.
        The values of sh:minLength in a shape are literals with datatype xsd:integer.

        Args:
            value (int): Min length of RDF literal

        Returns:
            SHACLAnnotation.MIN_LENGTH (dataclass)
        """
        return SHACLAnnotation.MIN_LENGTH(value)

    @staticmethod
    def maxLength(value: int) -> MAX_LENGTH:
        """SHACL maxLength annotation.

        The maximum length of an RDF literal.
        The values of sh:maxLength in a shape are literals with datatype xsd:integer.

        Args:
            value (int): Max length of RDF literal

        Returns:
            SHACLAnnotation.MAX_LENGTH (dataclass)
        """
        return SHACLAnnotation.MAX_LENGTH(value)

    @staticmethod
    def minInclusive(value: float) -> MIN_INCLUSIVE:
        """SHACL minInclusive annotation.

        The minimum value of an RDF literal.
        The values of sh:minInclusive in a shape are literals with numeric datatype.
        A shape has at most one value for sh:minInclusive.

        Args:
            value (int | float): Min inclusive value of RDF literal

        Returns:
            SHACLAnnotation.MIN_INCLUSIVE (dataclass)
        """
        return SHACLAnnotation.MIN_INCLUSIVE(value)

    @staticmethod
    def maxInclusive(value: float) -> MAX_INCLUSIVE:
        """SHACL maxInclusive annotation.

        The maximum value of an RDF literal.
        The values of sh:maxInclusive in a shape are literals with numeric datatype.
        A shape has at most one value for sh:maxInclusive.

        Args:
            value (int | float): Max inclusive value of RDF literal

        Returns:
            SHACLAnnotation.MAX_INCLUSIVE (dataclass)
        """
        return SHACLAnnotation.MAX_INCLUSIVE(value)

    @staticmethod
    def minExclusive(value: float) -> MIN_EXCLUSIVE:
        """SHACL minExclusive annotation.

        The minimum value of an RDF literal.
        The values of sh:minExclusive in a shape are literals with numeric datatype.
        A shape has at most one value for sh:minExclusive.

        Args:
            value (int | float): Min exclusive value of RDF literal

        Returns:
            SHACLAnnotation.MIN_EXCLUSIVE (dataclass)
        """
        return SHACLAnnotation.MIN_EXCLUSIVE(value)

    @staticmethod
    def maxExclusive(value: float) -> MAX_EXCLUSIVE:
        """SHACL maxExclusive annotation.

        The maximum value of an RDF literal.
        The values of sh:maxExclusive in a shape are literals with numeric datatype.
        A shape has at most one value for sh:maxExclusive.

        Args:
            value (int | float): Max exclusive value of RDF literal

        Returns:
            SHACLAnnotation.MAX_EXCLUSIVE (dataclass)
        """
        return SHACLAnnotation.MAX_EXCLUSIVE(value)

    @staticmethod
    def nodeKind(value: str) -> NODE_KIND:
        """SHACL nodeKind annotation.

        The kind of node that an RDF literal must be.
        The values of sh:nodeKind in a shape are literals with datatype xsd:anyURI.
        A shape has at most one value for sh:nodeKind.

        Args:
            value (str): Instance of node kind

        Returns:
            SHACLAnnotation.NODE_KIND (dataclass)
        """
        return SHACLAnnotation.NODE_KIND(value)

    @staticmethod
    def shclass(value: str) -> CLASS:
        """SHACL class annotation.

        The class of an RDF literal must be an instance of the given class.
        The values of sh:class in a shape are literals with datatype xsd:anyURI.
        A shape has at most one value for sh:class.

        Args:
            value (str): IRI of class

        Returns:
            SHACLAnnotation.CLASS (dataclass)
        """
        return SHACLAnnotation.CLASS(value)

    @staticmethod
    def severity(value: str) -> SEVERITY:
        """SHACL serverity annotation.

        States the severity of the constraint violation as one of:
            sh:Info, sh:Warning, sh:Violation

        Args:
            value (str): IRI of severity

        Returns:
            SHACLAnnotation.CLASS (dataclass)
        """
        return SHACLAnnotation.SEVERITY(value)
