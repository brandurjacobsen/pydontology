import pytest
from rdflib import OWL, RDF, RDFS, Graph, Namespace

from pydontology.pydontology import BaseContext, JSONLDGraph
from pydontology.settings import Settings

# See conftest.py for TestModel definition


@pytest.fixture(
    params=[
        # Use class docstrings as rdfs:comment for ontology classes
        {"DOCSTRING_AS_COMMENT": False},
        # Use class name as rdfs:label for ontology classes
        {"CLASS_NAME_AS_LABEL": False},
        # Use field name as rdfs:label for ontology properties
        {"FIELD_NAME_AS_LABEL": True},
        # Use field descriptions as rdfs:comment for ontology properties
        # (Can not be used if property is defined in multiple ontology classes)
        {"DESCRIPTION_AS_COMMENT": False},
        # Use origin class as rdfs:domain for ontology properties
        # (Can not be used if property is defined in multiple ontology classes)
        {"ORIGIN_AS_DOMAIN": False},
        # Default parent (rdfs:subClassOf) for ontology classes inheriting from Entity
        {"SUBCLASS_OF_DEFAULT": "owl:Thing"},
    ]
)
def onto_graph_settings(TestModel, request):
    """Fixture providing the generated ontology graph

    This one is parameterized by different settings
    """

    cfg = Settings.model_validate(request.param)
    return TestModel.ontology_graph(settings=cfg)
