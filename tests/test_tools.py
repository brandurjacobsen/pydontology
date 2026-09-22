import pytest

pytest.importorskip("jinja2")

from pydontology.tools import llm_tools

TOOL_KEYS = {"get_class_description", "get_property_description"}


def test_llm_tools_returns_two_callables(TestModel):
    tools = llm_tools(TestModel)
    assert set(tools) == TOOL_KEYS


def test_get_class_description(TestModel):
    tools = llm_tools(TestModel)
    out = tools["get_class_description"]("Employee")
    assert "Class: Employee" in out
    assert "IRI: ex:Employee" in out
    assert "An employee, subclass of Person" in out
    assert "Subclass of: ex:Person" in out


def test_get_class_description_base_class(TestModel):
    tools = llm_tools(TestModel)
    out = tools["get_class_description"]("Person")
    assert "Class: Person" in out
    assert "A person, subclass of Entity" in out
    assert "Subclass of: owl:Thing" in out


def test_get_class_description_intersection(TestModel):
    tools = llm_tools(TestModel)
    out = tools["get_class_description"]("DualIncome")
    assert "Intersection of: ex:Contractor, ex:Employee" in out


def test_get_property_description(TestModel):
    tools = llm_tools(TestModel)
    out = tools["get_property_description"]("manager")
    assert "Property: manager" in out
    assert "IRI: ex:manager" in out
    assert "owl:ObjectProperty" in out
    assert "owl:TransitiveProperty" in out
    assert "Link to manager" in out
    assert "Domain: ex:Employee" in out
    assert "Range: ex:Manager" in out


def test_get_property_description_symmetric(TestModel):
    tools = llm_tools(TestModel)
    out = tools["get_property_description"]("knows")
    assert "owl:ObjectProperty" in out
    assert "owl:SymmetricProperty" in out
    assert "A friend or colleague" in out
    assert "Domain: ex:Person" in out
    # No RDFS.range annotation -> no Range line (and no Jinja 'range' global leak)
    assert "Range:" not in out


def test_get_property_description_datatype_no_range(TestModel):
    tools = llm_tools(TestModel)
    out = tools["get_property_description"]("age")
    assert "owl:DatatypeProperty" in out
    assert "xsd:integer" in out
    assert "Range:" not in out


def test_not_found(TestModel):
    tools = llm_tools(TestModel)
    assert tools["get_class_description"]("Nope") == "Class 'Nope' not found."
    assert tools["get_property_description"]("Nope") == "Property 'Nope' not found."


def test_custom_template(TestModel):
    tools = llm_tools(TestModel, templates={"class": "{{ id }}!"})
    assert tools["get_class_description"]("Person") == "ex:Person!"
    # The property template should remain the default
    assert "Property: manager" in tools["get_property_description"]("manager")


def test_unknown_template_key(TestModel):
    with pytest.raises(ValueError):
        llm_tools(TestModel, templates={"clazz": "{{ id }}"})


def test_no_jsonld_aliases_in_output(TestModel):
    tools = llm_tools(TestModel)
    for cls in TestModel.classes:
        out = tools["get_class_description"](cls.id)
        assert "@" not in out
        assert "rdfs:" not in out
    for prop in TestModel.properties:
        out = tools["get_property_description"](prop.id)
        assert "@" not in out
        assert "rdfs:" not in out
