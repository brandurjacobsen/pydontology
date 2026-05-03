import os
import json

import pytest

from pydontology.models import Entity, Relation
from pydontology.pydontology import Pydontology
from pydontology.settings import Settings


class Sample(Entity):
    name: str
    age: int
    friend: Relation | None = None
    tags: list[str] = []


class WithMeta(Entity):
    meta: dict[str, str]


def test_serialize_literals_as_typeval_enabled():
    cfg = Settings.model_validate({"SERIALIZE_LITERALS_AS_TYPEVAL": True})
    os.environ["PYDONTOLOGY_TYPE_STRICT_MODE"] = "0"
    onto = Pydontology(ontology=Sample)

    try:
        onto.ontology_graph(settings=cfg)
        model = onto.jsonld_graph()
        sample = Sample(
            id="S1",
            name="Jane",
            age=27,
            friend=Relation(id="S2"),
            tags=["a", "b"],
        )
        graph = model(graph=[sample])

        data = graph.model_dump()
        node = data["graph"][0]
        assert node["name"] == {"@value": "Jane", "@type": "xsd:string"}
        assert node["age"] == {"@value": 27, "@type": "xsd:integer"}
        assert node["@id"] == "S1"
        assert node["friend"] == {"@id": "S2"}
        assert node["tags"] == [
            {"@value": "a", "@type": "xsd:string"},
            {"@value": "b", "@type": "xsd:string"},
        ]

        json_data = json.loads(graph.model_dump_json())
        json_node = json_data["graph"][0]
        assert json_node["name"] == {"@value": "Jane", "@type": "xsd:string"}
        assert json_node["age"] == {"@value": 27, "@type": "xsd:integer"}
        assert json_node["@id"] == "S1"
        assert json_node["friend"] == {"@id": "S2"}
        assert json_node["tags"] == [
            {"@value": "a", "@type": "xsd:string"},
            {"@value": "b", "@type": "xsd:string"},
        ]
    finally:
        os.environ.pop("PYDONTOLOGY_TYPE_STRICT_MODE", None)
        Entity._serialize_literals_as_typeval = False
        Entity._type_strict_mode = True


def test_serialize_literals_as_typeval_non_strict_passes_through():
    cfg = Settings.model_validate(
        {"SERIALIZE_LITERALS_AS_TYPEVAL": True, "TYPE_STRICT_MODE": False}
    )
    os.environ["PYDONTOLOGY_TYPE_STRICT_MODE"] = "0"
    onto = Pydontology(ontology=WithMeta)

    try:
        onto.ontology_graph(settings=cfg)
        model = onto.jsonld_graph()
        sample = WithMeta(id="S1", meta={"k": "v"})
        graph = model(graph=[sample])

        data = graph.model_dump()
        node = data["graph"][0]
        assert node["meta"] == {"k": "v"}
    finally:
        os.environ.pop("PYDONTOLOGY_TYPE_STRICT_MODE", None)
        Entity._serialize_literals_as_typeval = False
        Entity._type_strict_mode = True


def test_serialize_literals_as_typeval_strict_raises():
    cfg = Settings.model_validate({"SERIALIZE_LITERALS_AS_TYPEVAL": True})
    os.environ["PYDONTOLOGY_TYPE_STRICT_MODE"] = "0"
    onto = Pydontology(ontology=WithMeta)

    try:
        onto.ontology_graph(settings=cfg)
        model = onto.jsonld_graph()
        sample = WithMeta(id="S1", meta={"k": "v"})
        graph = model(graph=[sample])

        with pytest.raises(ValueError, match="TYPE_STRICT_MODE"):
            graph.model_dump()
    finally:
        os.environ.pop("PYDONTOLOGY_TYPE_STRICT_MODE", None)
        Entity._serialize_literals_as_typeval = False
        Entity._type_strict_mode = True
