from typing import Annotated

import pytest
from pydantic import Field

from pydontology import APIAnnotation as API
from pydontology import Entity, Pydontology


class FakeQueryResult:
    def __init__(self, data):
        self._data = data

    def convert(self):
        return self._data


class FakeSPARQLWrapper:
    def __init__(self, data):
        self.data = data
        self.query_text = None

    def setQuery(self, query):
        self.query_text = query

    def query(self):
        return FakeQueryResult(self.data)


@pytest.fixture
def sparql_api_model():
    class Widget(Entity):
        name: Annotated[str, API.route("GET")] = Field(description="Widget name")

    onto = Pydontology(
        ontology=Annotated[
            Widget,
            API.route("GET"),
            API.route("GET", path="{id}"),
        ]
    )
    return onto


def test_generate_api_sparql_handlers(sparql_api_model):
    pytest.importorskip("fastapi")
    from fastapi.routing import APIRoute
    from rdflib import Graph, Literal, Namespace, RDF

    vocab = Namespace("http://example.com/vocab/")
    graph = Graph()
    widget_id = vocab["widget1"]
    graph.add((widget_id, RDF.type, vocab.Widget))
    graph.add((widget_id, vocab.name, Literal("Widget 1")))

    data = graph.serialize(format="xml")
    wrapper = FakeSPARQLWrapper(data)

    api = sparql_api_model.generate_api(sparql_wrapper=wrapper)
    routes = [route for route in api.routes if isinstance(route, APIRoute)]

    def find_route(path, method):
        for route in routes:
            if route.path == path and method in route.methods:
                return route
        return None

    list_route = find_route("/widget", "GET")
    assert list_route is not None
    list_result = list_route.endpoint()
    assert len(list_result) == 1
    assert list_result[0].name == "Widget 1"

    detail_route = find_route("/widget/{id}", "GET")
    assert detail_route is not None
    detail_result = detail_route.endpoint(id="widget1")
    assert detail_result.name == "Widget 1"
