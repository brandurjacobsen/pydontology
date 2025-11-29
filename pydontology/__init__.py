from .pydontology import Entity, JSONLDGraph, Relation, make_model
from .rdfs import RDFSAnnotation
from .shacl import SHACLAnnotation

# from .owl import OWLAnnotation

__all__ = [
    "Entity",
    "Relation",
    "JSONLDGraph",
    "RDFSAnnotation",
    "SHACLAnnotation",
    "make_model",
]
