from typing import Annotated, Optional

import pytest
from pydantic import Field
from rdflib import OWL, RDF, RDFS, Graph, Namespace

from pydontology import Entity, JSONLDGraph, RDFSAnnotation, Relation, make_model


@pytest.fixture
def sample_entities():
    # Define test entity classes with inheritance
    class Person(Entity):
        """A person entity"""

        name: str = Field(description="Person's name")
        age: Optional[int] = Field(default=None, description="Person's age")

    class Employee(Person):
        """An employee entity, inherits from Person"""

        employee_id: str = Field(description="Employee ID")
        manager: Annotated[Optional[Relation], RDFSAnnotation.range("Manager")] = Field(
            default=None, description="Link to manager"
        )

    class Manager(Employee):
        """A manager entity, inherits from Employee"""

        department: str = Field(description="Department name")

    """Fixture providing sample entity instances"""
    person1 = Person(id="person/1", name="Alice", age=30)
    employee1 = Employee(
        id="employee/1",
        name="Bob",
        age=25,
        employee_id="E001",
        manager=Relation(id="manager/1"),
    )
    manager1 = Manager(
        id="manager/1",
        name="Charlie",
        age=40,
        employee_id="M001",
        department="Engineering",
    )
    return [person1, employee1, manager1]


@pytest.fixture
def sample_graph(sample_entities):
    """Fixture providing a JSONLDGraph with sample entities"""
    return JSONLDGraph(
        context={"@vocab": "http://example.org/", "@base": "http://example.org/"},
        graph=sample_entities,
    )


@pytest.fixture
def person_model():
    """Fixture providing the Person entity class"""

    class Person(Entity):
        """A person entity"""

        name: str = Field(description="Person's name")
        age: Optional[int] = Field(default=None, description="Person's age")

    class Employee(Person):
        """An employee entity, inherits from Person"""

        employee_id: str = Field(description="Employee ID")
        manager: Annotated[Optional[Relation], RDFSAnnotation.range("Manager")] = Field(
            default=None, description="Link to manager"
        )

    class Manager(Employee):
        """A manager entity, inherits from Employee"""

        department: str = Field(description="Department name")

    return make_model(Person, name="PersonModel")


def test_rdflib_parse_jsonld_graph(sample_graph):
    """Test that rdflib can parse the JSONLDGraph output"""
    # Serialize the graph to JSON-LD
    jsonld_str = sample_graph.model_dump_json()
    print(jsonld_str)
    # Parse with rdflib
    g = Graph()
    g.parse(data=jsonld_str, format="json-ld")
    for triple in g:
        print(triple)

    # Verify we have triples
    assert len(g) > 0

    # Define namespace
    EX = Namespace("http://example.org/")

    # Verify entities exist (URIs are expanded with @vocab)
    person1_uri = EX["person/1"]
    employee1_uri = EX["employee/1"]
    manager1_uri = EX["manager/1"]

    # Check that entities have types (expanded with @vocab)
    assert (person1_uri, RDF.type, EX.Person) in g
    assert (employee1_uri, RDF.type, EX.Employee) in g
    assert (manager1_uri, RDF.type, EX.Manager) in g

    # Check properties exist (using None to match any object)
    name_objects = g.value(subject=person1_uri, predicate=EX["name"])
    print("Name object is:", name_objects)
    # assert len(list(name_objects)) > 0

    # employee_id_triples = list(g.triples((employee1_uri, EX.employee_id, None)))
    # assert len(employee_id_triples) > 0

    # department_triples = list(g.triples((manager1_uri, EX.department, None)))
    # assert len(department_triples) > 0

    ## Check relation exists
    # assert (employee1_uri, EX.manager, manager1_uri) in g
