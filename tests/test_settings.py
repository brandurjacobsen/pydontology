import pytest
from rdflib import OWL, RDF, RDFS, Graph, Namespace

from pydontology.pydontology import BaseContext, JSONLDGraph
from pydontology.settings import Settings

# See conftest.py for TestModel definition


@pytest.fixture(
    params=[
        {"DOCSTRING_AS_COMMENT": True},
        {"DOCSTRING_AS_COMMENT": False},
    ]
)
def onto_graph(TestModel, request):
    """Fixture providing the generated ontology graph"""
    cfg = Settings.model_validate(request.param)
    print(cfg)
    return TestModel.ontology_graph()
