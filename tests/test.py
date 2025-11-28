import json
import pytest
from pydontology import Entity, Relation, JSONLDGraph, RDFSAnnotation, make_model
from pydantic import Field
from typing import Optional, Annotated

# Define test entity classes with inheritance
class Person(Entity):
    """A person entity"""
    name: str = Field(description="Person's name")
    age: Optional[int] = Field(default=None, description="Person's age")


class Employee(Person):
    """An employee entity, inherits from Person"""
    employee_id: str = Field(description="Employee ID")
    manager: Annotated[Optional[Relation], RDFSAnnotation.range('Manager')] = Field(default=None, description="Link to manager")


class Manager(Employee):
    """A manager entity, inherits from Employee"""
    department: str = Field(description="Department name")


@pytest.fixture
def sample_entities():
    """Fixture providing sample entity instances"""
    person1 = Person(id="person/1", name="Alice", age=30)
    employee1 = Employee(
        id="employee/1",
        name="Bob",
        age=25,
        employee_id="E001",
        manager=Relation(id="employee/2")
    )
    manager1 = Manager(
        id="manager/1",
        name="Charlie",
        age=40,
        employee_id="M001",
        department="Engineering"
    )
    return [person1, employee1, manager1]


@pytest.fixture
def sample_graph(sample_entities):
    """Fixture providing a JSONLDGraph with sample entities"""
    return JSONLDGraph(
        context={"@vocab": "http://example.org/vocab/", "@base": "http://example.org/"},
        graph=sample_entities
    )


@pytest.fixture
def person_model():
    """Fixture providing the model created from Person entity"""
    return make_model(Person, name="PersonModel")


@pytest.fixture
def ontology(person_model):
    """Fixture providing the generated ontology"""
    return person_model.ontology_graph()


def test_ontology_returns_jsonld_graph(person_model):
    """Test that ontology_graph returns a JSONLDGraph instance"""
    ontology = person_model.ontology_graph()
    assert isinstance(ontology, JSONLDGraph)


def test_ontology_structure(ontology):
    """Test that ontology has correct top-level structure"""
    ontology_dict = ontology.model_dump(by_alias=True)

    assert "@context" in ontology_dict
    assert "@graph" in ontology_dict
    assert "rdfs" in ontology_dict["@context"]
    assert "owl" in ontology_dict["@context"]
    assert ontology_dict["@context"]["@vocab"] == "http://example.com/vocab/"
    assert ontology_dict["@context"]["rdfs"] == "http://www.w3.org/2000/01/rdf-schema#"
    assert ontology_dict["@context"]["owl"] == "http://www.w3.org/2002/07/owl#"


def test_ontology_classes_present(ontology):
    """Test that all expected classes are present in ontology"""
    ontology_dict = ontology.model_dump(by_alias=True)
    classes = [item for item in ontology_dict["@graph"] if item.get("@type") == "rdfs:Class"]
    class_names = {cls["@id"] for cls in classes}

    assert len(classes) == 3
    assert "Person" in class_names
    assert "Employee" in class_names
    assert "Manager" in class_names


def test_ontology_inheritance(ontology):
    """Test that inheritance relationships are correctly represented"""
    ontology_dict = ontology.model_dump(by_alias=True)
    classes = [item for item in ontology_dict["@graph"] if item.get("@type") == "rdfs:Class"]

    # Employee should inherit from Person
    employee_class = next(cls for cls in classes if cls["@id"] == "Employee")
    assert "rdfs:subClassOf" in employee_class
    assert employee_class["rdfs:subClassOf"]["@id"] == "Person"

    # Manager should inherit from Employee
    manager_class = next(cls for cls in classes if cls["@id"] == "Manager")
    assert "rdfs:subClassOf" in manager_class
    assert manager_class["rdfs:subClassOf"]["@id"] == "Employee"

    # Person should not have subClassOf (it's the base)
    person_class = next(cls for cls in classes if cls["@id"] == "Person")
    assert  person_class["rdfs:subClassOf"] is None


def test_ontology_class_descriptions(ontology):
    """Test that class descriptions are included"""
    ontology_dict = ontology.model_dump(by_alias=True)
    classes = [item for item in ontology_dict["@graph"] if item.get("@type") == "rdfs:Class"]

    person_class = next(cls for cls in classes if cls["@id"] == "Person")
    assert person_class.get("rdfs:comment") == "A person entity"

    employee_class = next(cls for cls in classes if cls["@id"] == "Employee")
    assert employee_class.get("rdfs:comment") == "An employee entity, inherits from Person"

    manager_class = next(cls for cls in classes if cls["@id"] == "Manager")
    assert manager_class.get("rdfs:comment") == "A manager entity, inherits from Employee"


def test_ontology_properties_present(ontology):
    """Test that all expected properties are present"""
    ontology_dict = ontology.model_dump(by_alias=True)
    properties = [item for item in ontology_dict["@graph"] if item.get("@type") in ["owl:ObjectProperty", "owl:DatatypeProperty"]]
    property_names = {prop["@id"] for prop in properties}

    assert len(properties) == 5
    assert "name" in property_names
    assert "age" in property_names
    assert "employee_id" in property_names
    assert "manager" in property_names
    assert "department" in property_names


def test_ontology_property_types(ontology):
    """Test that properties have correct types (ObjectProperty vs DatatypeProperty)"""
    ontology_dict = ontology.model_dump(by_alias=True)
    properties = [item for item in ontology_dict["@graph"] if item.get("@type") in ["owl:ObjectProperty", "owl:DatatypeProperty"]]

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
    assert department_prop["@type"] == "owl:DatatypeProperty"


def test_ontology_property_descriptions(ontology):
    """Test that property descriptions are included"""
    ontology_dict = ontology.model_dump(by_alias=True)
    properties = [item for item in ontology_dict["@graph"] if item.get("@type") in ["owl:ObjectProperty", "owl:DatatypeProperty"]]

    manager_prop = next(prop for prop in properties if prop["@id"] == "manager")
    assert manager_prop.get("rdfs:comment") == "Link to manager"

    name_prop = next(prop for prop in properties if prop["@id"] == "name")
    assert name_prop.get("rdfs:comment") == "Person's name"

    age_prop = next(prop for prop in properties if prop["@id"] == "age")
    assert age_prop.get("rdfs:comment") == "Person's age"


def test_ontology_property_domains(ontology):
    """Test that properties have correct domain assignments"""
    ontology_dict = ontology.model_dump(by_alias=True)
    properties = [item for item in ontology_dict["@graph"] if item.get("@type") in ["owl:ObjectProperty", "owl:DatatypeProperty"]]

    name_prop = next(prop for prop in properties if prop["@id"] == "name")
    assert name_prop["rdfs:domain"]["@id"] == "Person"

    employee_id_prop = next(prop for prop in properties if prop["@id"] == "employee_id")
    assert employee_id_prop["rdfs:domain"]["@id"] == "Employee"

    department_prop = next(prop for prop in properties if prop["@id"] == "department")
    assert department_prop["rdfs:domain"]["@id"] == "Manager"


def test_ontology_property_range(ontology):
    """Test that rdfs:range is correctly set from Annotated metadata"""
    ontology_dict = ontology.model_dump(by_alias=True)
    properties = [item for item in ontology_dict["@graph"] if item.get("@type") in ["owl:ObjectProperty", "owl:DatatypeProperty"]]

    manager_prop = next(prop for prop in properties if prop["@id"] == "manager")
    assert "rdfs:range" in manager_prop
    assert manager_prop["rdfs:range"]["@id"] == "Manager"


def test_ontology_output_format(ontology, capsys):
    """Test that ontology can be serialized to JSON"""
    # Should be JSON serializable
    json_output = ontology.model_dump_json(by_alias=True, exclude_none=True)
    assert json_output is not None
    assert len(json_output) > 0

    # Should be valid JSON that can be parsed back
    parsed = json.loads(json_output)
    assert "@context" in parsed
    assert "@graph" in parsed
