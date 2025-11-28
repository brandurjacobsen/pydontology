from .pydontology import Entity, Relation, JSONLDGraph, make_model, OntologyClass, OntologyProperty, PropertyShape, NodeShape
from .rdfs import RDFSAnnotation
from .shacl import SHACLAnnotation
#from .owl import OWLAnnotation

__all__ = ["Entity", "Relation", "JSONLDGraph", "RDFSAnnotation", "SHACLAnnotation", "make_model", "OntologyClass", "OntologyProperty", "PropertyShape", "NodeShape"]
