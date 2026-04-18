"""
Pydontology - Ontologies the Pydantic way.

This package enables building RDF ontologies using Pydantic model classes.
"""

__version__ = "0.1.7"

from .owl import OWLAnnotation
from .pydontology import (
    BaseContext,
    Entity,
    Pydontology,
    Relation,
)
from .rdfs import RDFSAnnotation
from .settings import Settings
from .shacl import SHACLAnnotation
from .validators import (
    val_datatype,
    val_no_whitespace,
    val_node_kind,
    val_non_negative_int,
    val_positive_int,
    val_regex_pattern,
    val_severity_cls,
)

__all__ = [
    "BaseContext",
    "Entity",
    "Relation",
    "Pydontology",
    "RDFSAnnotation",
    "OWLAnnotation",
    "SHACLAnnotation",
    "Settings",
    "val_datatype",
    "val_no_whitespace",
    "val_node_kind",
    "val_non_negative_int",
    "val_positive_int",
    "val_regex_pattern",
    "val_severity_cls",
]
