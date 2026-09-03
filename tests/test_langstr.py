import json
from typing import Optional

import pytest
from pydantic import Field, ValidationError
from rdflib import Dataset, Namespace

from pydontology import Entity, LangStr, Pydontology, Settings
from pydontology.pydontology import BaseContext


class Named(Entity):
    """An entity with a language tagged literal field"""

    name: LangStr = Field(description="Name as language tagged literal")
    nick: Optional[LangStr] = Field(default=None, description="Nickname")


@pytest.fixture
def onto():
    return Pydontology(Named)


def test_strict_mode_accepts_langstr(onto):
    """LangStr fields (required and optional) pass TYPE_STRICT_MODE"""
    assert onto is not None


def test_langstr_property_is_datatype_property_without_xsd(onto):
    """LangStr fields yield owl:DatatypeProperty with no xsd rdf:type
    (language tagged literals carry no datatype in RDF)"""
    doc = json.loads(onto.ontology_graph().model_dump_json(exclude_none=True))
    by_id = {node["@id"]: node for node in doc["@graph"]}

    assert by_id["name"]["@type"] == ["owl:DatatypeProperty"]
    assert by_id["nick"]["@type"] == ["owl:DatatypeProperty"]


def test_no_default_shacl_property_shape_for_langstr(onto):
    """No default sh:datatype implies no default property shape for LangStr fields"""
    assert onto.shacl_graph().graph == []


def test_langstr_field_redefinable_with_same_type():
    """Redefining a LangStr property in another class with the same type is allowed"""

    class Other(Entity):
        name: LangStr

    Pydontology(Named | Other)  # should not raise


def test_json_schema_includes_langstr_def(onto):
    """The JSON-LD data graph schema exposes the LangStr definition"""
    schema = onto.jsonld_graph().model_json_schema()

    langstr = schema["$defs"]["LangStr"]
    assert langstr["type"] == "object"
    assert langstr["required"] == ["value", "language"]

    named = schema["$defs"]["Named"]
    assert named["properties"]["name"]["$ref"] == "#/$defs/LangStr"


def test_langstr_requires_value_and_language():
    with pytest.raises(ValidationError):
        LangStr(value="x")  # pyright: ignore
    with pytest.raises(ValidationError):
        LangStr(language="en")  # pyright: ignore


@pytest.mark.parametrize("tag", ["en", "en-US", "zh-CN"])
def test_langstr_accepts_valid_bcp47_tags(tag):
    langstr = LangStr(value="x", language=tag)
    assert langstr.language == tag


@pytest.mark.parametrize("tag", ["xx-YY", "english", "EN"])
def test_langstr_rejects_invalid_bcp47_tags(tag):
    with pytest.raises(ValidationError):
        LangStr(value="x", language=tag)


def test_langstr_serializes_as_language_tagged_literal(onto):
    person = Named(
        id="P1",
        name=LangStr(value="Jane", language="en"),
        nick=LangStr(value="J", language="en-GB"),
    )
    doc = json.loads(person.model_dump_json(exclude_none=True))
    assert doc["name"] == {"@value": "Jane", "@language": "en"}
    assert doc["nick"] == {"@value": "J", "@language": "en-GB"}


def test_langstr_data_graph_parses_to_language_tagged_literal(onto):
    graph_model = onto.jsonld_graph()
    person = Named(id="P1", name=LangStr(value="Jane", language="en"))
    data_graph = graph_model(graph=[person])

    ds = Dataset().parse(
        data=data_graph.model_dump_json(exclude_none=True), format="json-ld"
    )
    vocab = Namespace(BaseContext().vocab)
    literal = list(ds.objects(vocab.P1, vocab.name))[0]
    assert str(literal) == "Jane"
    assert literal.language == "en"


def test_literals_as_typeval_does_not_wrap_langstr(onto):
    """With LITERALS_AS_TYPEVAL on, LangStr fields must not be wrapped in
    TypeVal (or raise), since they already carry their own serialization"""
    onto._apply_settings(Settings(LITERALS_AS_TYPEVAL=True))
    person = Named(id="P1", name=LangStr(value="Jane", language="en"))
    doc = json.loads(person.model_dump_json(exclude_none=True))
    assert doc["name"] == {"@value": "Jane", "@language": "en"}
