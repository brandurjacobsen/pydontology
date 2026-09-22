import json

import pytest
from pydantic import Field

from pydontology import Entity, Pydontology, Settings
from pydontology.iri import qualify_iri


def test_qualify_iri_is_idempotent():
    assert qualify_iri("knows", "ex:") == "ex:knows"
    assert qualify_iri("ex:knows", "ex:") == "ex:knows"
    assert qualify_iri("owl:Thing", "ex:") == "owl:Thing"
    assert qualify_iri("http://example.com/x", "ex:") == "http://example.com/x"


def test_qualify_iri_namespace_style_prefix():
    assert qualify_iri("knows", "http://example.com/vocab/") == (
        "http://example.com/vocab/knows"
    )


def test_qualify_iri_requires_prefix_for_bare_name():
    with pytest.raises(ValueError):
        qualify_iri("knows", None)


class Thing(Entity):
    """A thing"""

    name: str = Field(description="A name")


def test_graph_ids_qualified_with_default_prefix():
    onto = Pydontology(Thing)
    doc = json.loads(onto.ontology_graph().model_dump_json(exclude_none=True))
    ids = {node["@id"] for node in doc["@graph"]}
    assert "ex:Thing" in ids
    assert "ex:name" in ids


def test_default_prefix_ns_injected_into_context():
    onto = Pydontology(Thing)
    graph = onto.ontology_graph(
        settings=Settings(
            DEFAULT_PREFIX="ex:", DEFAULT_PREFIX_NS="http://example.com/vocab/"
        )
    )
    doc = json.loads(graph.model_dump_json(exclude_none=True))
    assert doc["@context"]["ex"] == "http://example.com/vocab/"
    assert doc["@graph"][0]["@id"] == "ex:Thing"


def test_no_default_prefix_requires_qualification():
    onto = Pydontology(Thing)
    with pytest.raises(ValueError):
        onto.ontology_graph(settings=Settings(DEFAULT_PREFIX=None))


def test_entity_data_graph_qualifies_id_and_keys():
    onto = Pydontology(Thing)
    onto.jsonld_graph()  # applies default settings/prefix
    thing = Thing(id="t1", name="hello")
    doc = json.loads(thing.model_dump_json(exclude_none=True))
    assert doc["@id"] == "ex:t1"
    assert doc["@type"] == "ex:Thing"
    assert doc["ex:name"] == "hello"