import json

import pytest

from pydontology import IRI_REWRITER, Entity, Pydontology, Relation


def _rewrite(value: str) -> str:
    """Normalize a bare IRI to an absolute one."""
    return f"http://example.com/vocab/{value}"


class Thing(Entity):
    """A thing"""

    name: str
    knows: Relation | None = None
    acquaintances: list[Relation] | None = None


@pytest.fixture
def data_model(test_context):
    return Pydontology(Thing).jsonld_graph(context=test_context)


def _dump(graph, **kwargs):
    return json.loads(
        graph.model_dump_json(exclude_none=True, context={IRI_REWRITER: _rewrite}, **kwargs)
    )


def test_entity_id_rewritten_with_context(data_model):
    graph = data_model(graph=[Thing(id="Jane", name="Jane Doe")])
    doc = _dump(graph)
    assert doc["@graph"][0]["@id"] == "http://example.com/vocab/Jane"


def test_entity_id_unchanged_without_context(data_model):
    graph = data_model(graph=[Thing(id="Jane", name="Jane Doe")])
    doc = json.loads(graph.model_dump_json(exclude_none=True))
    assert doc["@graph"][0]["@id"] == "Jane"


def test_relation_references_rewritten(data_model):
    graph = data_model(
        graph=[
            Thing(
                id="Jane",
                name="Jane",
                knows=Relation(id="John"),
                acquaintances=[Relation(id="Bob"), Relation(id="Alice")],
            )
        ]
    )
    node = _dump(graph)["@graph"][0]
    assert node["@id"] == "http://example.com/vocab/Jane"
    assert node["knows"]["@id"] == "http://example.com/vocab/John"
    assert [r["@id"] for r in node["acquaintances"]] == [
        "http://example.com/vocab/Bob",
        "http://example.com/vocab/Alice",
    ]


def test_same_as_and_different_from_rewritten(data_model):
    graph = data_model(
        graph=[
            Thing(id="Jane", name="Jane", sameAs=[Relation(id="JaneDoe")]),
            Thing(id="John", name="John", differentFrom=Relation(id="Johnny")),
        ]
    )
    by_id = {node["@id"]: node for node in _dump(graph)["@graph"]}
    assert (
        by_id["http://example.com/vocab/Jane"]["owl:sameAs"][0]["@id"]
        == "http://example.com/vocab/JaneDoe"
    )
    assert (
        by_id["http://example.com/vocab/John"]["owl:differentFrom"]["@id"]
        == "http://example.com/vocab/Johnny"
    )


def test_top_level_graph_id_not_rewritten(data_model):
    graph = data_model(id="GraphIRI", graph=[Thing(id="Jane", name="Jane")])
    doc = _dump(graph)
    assert doc["@id"] == "GraphIRI"


def test_type_and_property_keys_not_rewritten(data_model):
    graph = data_model(
        graph=[Thing(id="Jane", name="Jane", knows=Relation(id="John"))]
    )
    node = _dump(graph)["@graph"][0]
    assert node["@type"] == "Thing"
    assert "name" in node


def test_model_dump_and_json_agree(data_model):
    graph = data_model(graph=[Thing(id="Jane", name="Jane")])
    context = {IRI_REWRITER: _rewrite}
    dumped = graph.model_dump(context=context)
    as_json = json.loads(graph.model_dump_json(context=context))
    assert dumped["@graph"][0]["@id"] == "http://example.com/vocab/Jane"
    assert as_json["@graph"][0]["@id"] == "http://example.com/vocab/Jane"


def test_unrelated_context_key_is_noop(data_model):
    graph = data_model(graph=[Thing(id="Jane", name="Jane")])
    doc = json.loads(graph.model_dump_json(context={"something_else": _rewrite}))
    assert doc["@graph"][0]["@id"] == "Jane"


def test_rewriter_is_deterministic_across_references(data_model):
    """Node ids and the references to them are rewritten to the same value."""
    graph = data_model(
        graph=[
            Thing(id="Jane", name="Jane", knows=Relation(id="John")),
            Thing(id="John", name="John"),
        ]
    )
    doc = _dump(graph)
    node_ids = {node["@id"] for node in doc["@graph"]}
    assert doc["@graph"][0]["knows"]["@id"] in node_ids
