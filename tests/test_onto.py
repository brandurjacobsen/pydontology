import json

import pytest

from pydontology import JSONLDGraph

# See conftest.py for ontology_model


@pytest.fixture
def onto_graph(ontology_model):
    """Fixture providing the generated ontology"""
    return ontology_model.ontology_graph()


def test_ontology_model_returns_jsonld_graph(onto_graph):
    """Test that onto_graph returns a JSONLDGraph instance"""
    assert isinstance(onto_graph, JSONLDGraph)


def test_onto_graph_structure(onto_graph):
    """Test that ontology graph has correct top-level structure"""
    ontology_dict = onto_graph.model_dump(by_alias=True)

    assert "@context" in ontology_dict
    assert "@graph" in ontology_dict
    assert "rdfs" in ontology_dict["@context"]
    assert "owl" in ontology_dict["@context"]


def test_ontology_classes_present(onto_graph):
    """Test that all expected classes are present in ontology graph"""
    ontology_dict = onto_graph.model_dump(by_alias=True)
    classes = [
        item for item in ontology_dict["@graph"] if item.get("@type") == "rdfs:Class"
    ]
    class_names = {cls["@id"] for cls in classes}

    assert len(classes) == 4
    assert "Person" in class_names
    assert "Employee" in class_names
    assert "Manager" in class_names
    assert "Department" in class_names


def test_ontology_inheritance(onto_graph):
    """Test that inheritance relationships are correctly represented"""
    ontology_dict = onto_graph.model_dump(by_alias=True)
    classes = [
        item for item in ontology_dict["@graph"] if item.get("@type") == "rdfs:Class"
    ]

    # Employee should inherit from Person
    employee_class = next(cls for cls in classes if cls["@id"] == "Employee")
    assert "rdfs:subClassOf" in employee_class
    assert employee_class["rdfs:subClassOf"]["@id"] == "Person"

    # Manager should inherit from Employee
    manager_class = next(cls for cls in classes if cls["@id"] == "Manager")
    assert "rdfs:subClassOf" in manager_class
    assert manager_class["rdfs:subClassOf"]["@id"] == "Employee"

    # Person should not have subClassOf (it inherits Entity)
    person_class = next(cls for cls in classes if cls["@id"] == "Person")
    assert person_class["rdfs:subClassOf"] is None

    # Department should not have subClassOf (it inherits Entity)
    department_class = next(cls for cls in classes if cls["@id"] == "Department")
    assert department_class["rdfs:subClassOf"] is None


def test_ontology_class_descriptions(onto_graph):
    """Test that class descriptions are included as rdfs:comment"""
    ontology_dict = onto_graph.model_dump(by_alias=True)
    classes = [
        item for item in ontology_dict["@graph"] if item.get("@type") == "rdfs:Class"
    ]

    person_class = next(cls for cls in classes if cls["@id"] == "Person")
    assert person_class.get("rdfs:comment") == "A person"

    employee_class = next(cls for cls in classes if cls["@id"] == "Employee")
    assert employee_class.get("rdfs:comment") == "An employee, inherits from Person"

    manager_class = next(cls for cls in classes if cls["@id"] == "Manager")
    assert manager_class.get("rdfs:comment") == "A manager, inherits from Employee"

    department_class = next(cls for cls in classes if cls["@id"] == "Department")
    assert department_class.get("rdfs:comment") == "A department, inherits from Entity"


def test_ontology_properties_present(onto_graph):
    """Test that all expected properties are present"""
    ontology_dict = onto_graph.model_dump(by_alias=True)
    properties = [
        item
        for item in ontology_dict["@graph"]
        if item.get("@type") in ["owl:ObjectProperty", "owl:DatatypeProperty"]
    ]
    property_names = {prop["@id"] for prop in properties}

    assert len(properties) == 5
    assert "name" in property_names
    assert "age" in property_names
    assert "employee_id" in property_names
    assert "manager" in property_names
    assert "department" in property_names


def test_ontology_property_types(onto_graph):
    """Test that properties have correct types (ObjectProperty vs DatatypeProperty)"""
    ontology_dict = onto_graph.model_dump(by_alias=True)
    properties = [
        item
        for item in ontology_dict["@graph"]
        if item.get("@type") in ["owl:ObjectProperty", "owl:DatatypeProperty"]
    ]

    # Relation fields should be ObjectProperty
    manager_prop = next(prop for prop in properties if prop["@id"] == "manager")
    assert manager_prop["@type"] == "owl:ObjectProperty"

    # Regular fields should be DatatypeProperty
    name_prop = next(prop for prop in properties if prop["@id"] == "name")
    assert name_prop["@type"] == "owl:DatatypeProperty"

    age_prop = next(prop for prop in properties if prop["@id"] == "age")
    assert age_prop["@type"] == "owl:DatatypeProperty"

    employee_id_prop = next(prop for prop in properties if prop["@id"] == "employee_id")
    assert employee_id_prop["@type"] == "owl:DatatypeProperty"

    department_prop = next(prop for prop in properties if prop["@id"] == "department")
    assert department_prop["@type"] == "owl:ObjectProperty"


def test_ontology_property_descriptions(onto_graph):
    """Test that property descriptions are included"""
    ontology_dict = onto_graph.model_dump(by_alias=True)
    properties = [
        item
        for item in ontology_dict["@graph"]
        if item.get("@type") in ["owl:ObjectProperty", "owl:DatatypeProperty"]
    ]

    manager_prop = next(prop for prop in properties if prop["@id"] == "manager")
    assert manager_prop.get("rdfs:comment") == "Link to manager"

    name_prop = next(prop for prop in properties if prop["@id"] == "name")
    assert name_prop.get("rdfs:comment") in ["Person's name", "Department name"]

    age_prop = next(prop for prop in properties if prop["@id"] == "age")
    assert age_prop.get("rdfs:comment") == "Person's age"

    dep_prop = next(prop for prop in properties if prop["@id"] == "department")
    assert dep_prop.get("rdfs:comment") == "Department IRI"


def test_ontology_property_domains(onto_graph):
    """Test that properties have correct domain assignments"""
    ontology_dict = onto_graph.model_dump(by_alias=True)
    properties = [
        item
        for item in ontology_dict["@graph"]
        if item.get("@type") in ["owl:ObjectProperty", "owl:DatatypeProperty"]
    ]

    name_prop = next(prop for prop in properties if prop["@id"] == "name")
    assert name_prop["rdfs:domain"]["@id"] in ["Person", "Department"]

    employee_id_prop = next(prop for prop in properties if prop["@id"] == "employee_id")
    assert employee_id_prop["rdfs:domain"]["@id"] == "Employee"

    department_prop = next(prop for prop in properties if prop["@id"] == "department")
    assert department_prop["rdfs:domain"]["@id"] == "Manager"


def test_ontology_property_range(onto_graph):
    """Test that rdfs:range is correctly set from Annotated metadata"""
    ontology_dict = onto_graph.model_dump(by_alias=True)
    properties = [
        item
        for item in ontology_dict["@graph"]
        if item.get("@type") in ["owl:ObjectProperty", "owl:DatatypeProperty"]
    ]

    manager_prop = next(prop for prop in properties if prop["@id"] == "manager")
    assert "rdfs:range" in manager_prop
    assert manager_prop["rdfs:range"]["@id"] == "Manager"

    dept_prop = next(prop for prop in properties if prop["@id"] == "department")
    assert "rdfs:range" in dept_prop
    assert dept_prop["rdfs:range"]["@id"] == "Department"


def test_ontology_output_format(onto_graph, capsys):
    """Test that ontology can be serialized to JSON"""

    json_output = onto_graph.model_dump_json(by_alias=True, exclude_none=True)
    assert json_output is not None
    assert len(json_output) > 0

    # Should be valid JSON that can be parsed back
    parsed = json.loads(json_output)
    assert "@context" in parsed
    assert "@graph" in parsed
