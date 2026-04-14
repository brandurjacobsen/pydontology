from typing import Annotated, List

from pydantic.dataclasses import dataclass
from pydantic.functional_validators import AfterValidator

# from .pydontology import Relation
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

    # Value Type Constraint Components
    @dataclass(frozen=True)
    class CLASS:
        """Dataclass that holds sh:class annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class DATATYPE:
        """Dataclass that holds sh:datatype annotation for a property."""

        value: Annotated[str, AfterValidator(val_datatype)]

    @dataclass(frozen=True)
    class NODE_KIND:
        """Dataclass that holds sh:nodeKind annotation for a property."""

        value: Annotated[str, AfterValidator(val_node_kind)]

    # Cardinality Constraint Components
    @dataclass(frozen=True)
    class MAX_COUNT:
        """Dataclass that holds sh:maxCount annotation for a property."""

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    @dataclass(frozen=True)
    class MIN_COUNT:
        """Dataclass that holds sh:minCount annotation for a property."""

        value: Annotated[int, AfterValidator(val_non_negative_int)]

    # Value Range Constraint Components
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

    # String-based Constraint Components
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
    class LANGUAGE_IN:
        """Dataclass that holds sh:languageIn annotation for a property."""

        value: List[str]

    @dataclass(frozen=True)
    class UNIQUE_LANG:
        """Dataclass that holds sh:uniqueLang annotation for a property."""

        value: bool

    # Property Pair Constraint Components
    @dataclass(frozen=True)
    class EQUALS:
        """Dataclass that holds sh:equals annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class DISJOINT:
        """Dataclass that holds sh:disjoint annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class LESS_THAN:
        """Dataclass that holds sh:lessThan annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass(frozen=True)
    class LESS_THAN_OR_EQUALS:
        """Dataclass that holds sh:lessThanOrEquals annotation for a property."""

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    # Other Constraint Components
    @dataclass(frozen=True)
    class CLOSED:
        """Dataclass that holds sh:closed annotation for a property."""

        value: bool

    @dataclass(frozen=True)
    class IGNORED_PROPERTIES:
        """Dataclass that holds sh:ignoredProperties annotation for a property."""

        value: List[str]

    @dataclass(frozen=True)
    class HAS_VALUE:
        """Dataclass that holds sh:hasValue annotation for a property."""

        value: str | int | float | bool

    @dataclass(frozen=True)
    class IN:
        """Dataclass that holds sh:in annotation for a property."""

        value: List[str | int | float | bool]

    # Validation parameters
    @dataclass(frozen=True)
    class SEVERITY:
        """Dataclass that holds sh:severity annotation for a property"""

        value: Annotated[str, AfterValidator(val_severity_cls)]

    # Non validating constructs
    @dataclass(frozen=True)
    class NAME:
        """Dataclass that holds sh:name annotation for a property."""

        value: str

    @dataclass(frozen=True)
    class DESCRIPTION:
        """Dataclass that holds sh:description annotation for a property."""

        value: str

    # METHODS:
    # Value Type Constraint Components
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

    # Cardinality Constraint Components
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

    # Value Range Constraint Components
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

    # String-based Constraint Components
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
    def languageIn(value: List[str]) -> LANGUAGE_IN:
        """SHACL languageIn annotation.

        Specifies that the language tag of RDF literals must be one of the given language tags.
        The values of sh:languageIn in a shape are lists of language tags (e.g., ["en", "fr", "de"]).
        A shape has at most one value for sh:languageIn.

        Args:
            value (list): List of allowed language tags (e.g., ["en", "en-US", "fr"])

        Returns:
            SHACLAnnotation.LANGUAGE_IN (dataclass)
        """
        return SHACLAnnotation.LANGUAGE_IN(value)

    @staticmethod
    def uniqueLang(value: bool) -> UNIQUE_LANG:
        """SHACL uniqueLang annotation.

        Specifies that no two value nodes may use the same language tag.
        The values of sh:uniqueLang in a shape are literals with datatype xsd:boolean.
        A shape has at most one value for sh:uniqueLang.

        Args:
            value (bool): True if language tags must be unique, False otherwise

        Returns:
            SHACLAnnotation.UNIQUE_LANG (dataclass)
        """
        return SHACLAnnotation.UNIQUE_LANG(value)

    # Property-pair Constraint Components
    @staticmethod
    def equals(value: str) -> EQUALS:
        """SHACL equals annotation.

        Specifies that the set of value nodes is equal to the set of values of the property at the given path.
        The values of sh:equals in a shape are property paths.
        A shape may have multiple values for sh:equals.

        Args:
            value (str): Property path that must have equal values

        Returns:
            SHACLAnnotation.EQUALS (dataclass)
        """
        return SHACLAnnotation.EQUALS(value)

    @staticmethod
    def disjoint(value: str) -> DISJOINT:
        """SHACL disjoint annotation.

        Specifies that the set of value nodes is disjoint with the set of values of the property at the given path.
        The values of sh:disjoint in a shape are property paths.
        A shape may have multiple values for sh:disjoint.

        Args:
            value (str): Property path that must have disjoint values

        Returns:
            SHACLAnnotation.DISJOINT (dataclass)
        """
        return SHACLAnnotation.DISJOINT(value)

    @staticmethod
    def lessThan(value: str) -> LESS_THAN:
        """SHACL lessThan annotation.

        Specifies that each value node is smaller than all the values of the property at the given path.
        The values of sh:lessThan in a shape are property paths.
        A shape may have multiple values for sh:lessThan.

        Args:
            value (str): Property path whose values must be greater than this property's values

        Returns:
            SHACLAnnotation.LESS_THAN (dataclass)
        """
        return SHACLAnnotation.LESS_THAN(value)

    @staticmethod
    def lessThanOrEquals(value: str) -> LESS_THAN_OR_EQUALS:
        """SHACL lessThanOrEquals annotation.

        Specifies that each value node is smaller than or equal to all the values of the property at the given path.
        The values of sh:lessThanOrEquals in a shape are property paths.
        A shape may have multiple values for sh:lessThanOrEquals.

        Args:
            value (str): Property path whose values must be greater than or equal to this property's values

        Returns:
            SHACLAnnotation.LESS_THAN_OR_EQUALS (dataclass)
        """
        return SHACLAnnotation.LESS_THAN_OR_EQUALS(value)

    # Other Constraint Components
    @staticmethod
    def closed(value: bool) -> CLOSED:
        """SHACL closed annotation.

        Specifies that a shape is closed, meaning that the focus node must not have any properties
        other than those explicitly declared in the shape (and optionally those listed in sh:ignoredProperties).
        The values of sh:closed in a shape are literals with datatype xsd:boolean.
        A shape has at most one value for sh:closed.

        Args:
            value (bool): True if the shape is closed, False otherwise

        Returns:
            SHACLAnnotation.CLOSED (dataclass)
        """
        return SHACLAnnotation.CLOSED(value)

    @staticmethod
    def ignoredProperties(value: List[str]) -> IGNORED_PROPERTIES:
        """SHACL ignoredProperties annotation.

        Specifies a list of properties that are ignored when checking if a closed shape is satisfied.
        The values of sh:ignoredProperties in a shape are lists of property paths.
        A shape has at most one value for sh:ignoredProperties.

        Args:
            value (List[str]): List of property paths to ignore in closed shapes

        Returns:
            SHACLAnnotation.IGNORED_PROPERTIES (dataclass)
        """
        return SHACLAnnotation.IGNORED_PROPERTIES(value)

    @staticmethod
    def hasValue(value: str | int | float | bool) -> HAS_VALUE:
        """SHACL hasValue annotation.

        Specifies that at least one value node is equal to the given RDF term.
        The values of sh:hasValue in a shape can be any RDF term.
        A shape may have multiple values for sh:hasValue.

        Args:
            value (str | int | float | bool): The required value

        Returns:
            SHACLAnnotation.HAS_VALUE (dataclass)
        """
        return SHACLAnnotation.HAS_VALUE(value)

    @staticmethod
    def shIn(value: List[str | int | float | bool]) -> IN:
        """SHACL sh:in annotation.

        Specifies that each value node is a member of a provided SHACL list.
        The values of sh:in in a shape are SHACL lists.
        A shape has at most one value for sh:in.

        Args:
            value (List[Relation | str | int | float | bool]): List of allowed values

        Returns:
            SHACLAnnotation.IN (dataclass)
        """
        return SHACLAnnotation.IN(value)

    # Validation parameter components
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

    # Non validating constructs
    @staticmethod
    def name(value: str) -> NAME:
        """SHACL name annotation.

        Provides a human-readable name for a property shape.
        The values of sh:name in a shape are literals.
        A shape has at most one value for sh:name.

        Args:
            value (str): Human-readable name

        Returns:
            SHACLAnnotation.NAME (dataclass)
        """
        return SHACLAnnotation.NAME(value)

    @staticmethod
    def description(value: str) -> DESCRIPTION:
        """SHACL description annotation.

        Provides a human-readable description for a property shape.
        The values of sh:description in a shape are literals.
        A shape has at most one value for sh:description.

        Args:
            value (str): Human-readable description

        Returns:
            SHACLAnnotation.DESCRIPTION (dataclass)
        """
        return SHACLAnnotation.DESCRIPTION(value)
