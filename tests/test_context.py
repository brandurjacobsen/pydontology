import json

from pydontology.pydontology import BaseContext


def test_default_context_omits_vocab_and_base():
    """With no explicit vocab/base, they must be omitted from @context, not
    emitted as null (a null @vocab is parsed differently from an absent one)"""
    for dumped in (
        BaseContext().model_dump_json(),
        BaseContext().model_dump_json(exclude_none=True),
    ):
        doc = json.loads(dumped)
        assert "@vocab" not in doc
        assert "@base" not in doc
        assert "@language" not in doc
        # The remaining default entries are still present
        assert doc["@version"] == 1.1
        assert doc["sh"] == "http://www.w3.org/ns/shacl#"


def test_default_context_dump_by_alias_omits_none():
    """model_dump (not just model_dump_json) must also drop unset entries"""
    dumped = BaseContext().model_dump(by_alias=True)
    assert "@vocab" not in dumped
    assert "@base" not in dumped
    assert "@language" not in dumped


def test_explicit_context_is_serialized():
    context = BaseContext(vocab="http://x.org/vocab/", base="http://x.org/", language="en")
    doc = json.loads(context.model_dump_json())
    assert doc["@vocab"] == "http://x.org/vocab/"
    assert doc["@base"] == "http://x.org/"
    assert doc["@language"] == "en"


def test_default_context_json_schema_has_optional_vocab_and_base():
    """vocab/base must be optional (string or null) with a null default"""
    schema = BaseContext.model_json_schema()
    for key in ("vocab", "base"):
        prop = schema["properties"][key]
        assert prop["default"] is None
        assert {"type": "null"} in prop["anyOf"]
    assert "required" not in schema
