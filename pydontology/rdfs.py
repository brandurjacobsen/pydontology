from typing import Annotated

from pydantic import AfterValidator
from pydantic.dataclasses import dataclass

from .validators import val_no_whitespace


class RDFSAnnotation:
    """Helper class for RDFS annotations."""

    @dataclass
    class DOMAIN:
        """Metadata to specify rdfs:domain for a property.

        rdfs:domain is an instance of rdf:Property that is used to state that
        any resource that has a given property is an instance of one or more classes.
        """

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @dataclass
    class RANGE:
        """Metadata to specify rdfs:range for a property.

        rdfs:range is an instance of rdf:Property that is used to state
        that the values of a property are instances of one or more classes.
        """

        value: Annotated[str, AfterValidator(val_no_whitespace)]

    @staticmethod
    def domain(value: str) -> DOMAIN:
        """RDFSAnnotation.DOMAIN factory"""
        return RDFSAnnotation.DOMAIN(value=value)

    @staticmethod
    def range(value: str) -> RANGE:
        """RDFSAnnotation.RANGE factory"""
        return RDFSAnnotation.RANGE(value=value)
