from typing import Annotated, List, Optional

import pytest
from pydantic import Field

from pydontology.api import APIAnnotation as API
from pydontology.models import Entity, Relation
from pydontology.owl import (
    OWLAnnotation as OWL,
)
from pydontology.pydontology import Pydontology
from pydontology.rdfs import (
    RDFSAnnotation as RDFS,
)
from pydontology.shacl import (
    SHACLAnnotation as SH,
)


class Person(Entity):
    """A person, subclass of Entity"""

    name: Annotated[
        str,
        SH.minCount(1),
        SH.minLength(1),
        SH.maxLength(100),
    ] = Field(description="Person's name")
    age: Annotated[
        Optional[int],
        OWL.functionalProperty(True),
        SH.minInclusive(0),
        SH.maxInclusive(150),
        SH.datatype("xsd:integer"),
        SH.severity("sh:Warning"),
    ] = Field(default=None, description="Person's age in years")
    knows: Annotated[
        Optional[Relation | list[Relation]], OWL.symmetricProperty(True)
    ] = Field(default=None, description="A friend or colleague")
    acquaintance: Annotated[
        Optional[List[Relation] | Relation], RDFS.subPropertyOf(Relation(id="knows"))
    ]
    works_for: Annotated[Optional[Relation], OWL.equivalentProperty("works_at")] = (
        Field(default=None)
    )
    has_contract_with: Annotated[Relation, RDFS.range(Relation(id="Company"))]


class Employee(Person):
    """An employee, subclass of Person"""

    employee_id: Annotated[
        str,
        OWL.functionalProperty(True),
        OWL.inverseFunctionalProperty(True),
        SH.pattern(r"^E\d{3}$"),
    ] = Field(description="Employee ID")
    manager: Annotated[
        Optional[Relation],
        RDFS.range("Manager"),
        OWL.transitiveProperty(True),
        SH.shclass("Manager"),
        SH.minCount(1),
        SH.maxCount(1),
    ] = Field(default=None, description="Link to manager")
    department: Annotated[
        Relation,
        RDFS.range("Department"),
        SH.minCount(1),
    ] = Field(description="Department IRI")
    company: Annotated[
        Relation,
        RDFS.range("Company"),
        SH.shclass("Company"),
    ]


class Manager(Employee):
    """A manager, subclass of Employee"""

    head_of: Annotated[
        Optional[Relation],
        RDFS.range("Department"),
    ] = Field(default=None, description="Department manager heads")
    vice_head_of: Annotated[
        Optional[Relation],
        RDFS.range("Department"),
    ] = Field(default=None, description="Department manager is vice head of")


class Department(Entity):
    """A department, subclass of Entity"""

    name: Annotated[str, SH.minLength(1), SH.maxLength(50)] = Field(
        description="Department's name"
    )
    company: Annotated[
        Relation,
        RDFS.range("Company"),
        SH.shclass("Company"),
    ]
    head: Annotated[
        Relation,
        RDFS.range("Manager"),
        OWL.inverseOf("head_of"),
        SH.minCount(1),
        SH.maxCount(1),
        SH.disjoint("vice_head"),
    ]
    vice_head: Annotated[
        Optional[Relation],
        RDFS.range("Manager"),
        OWL.inverseOf("vice_head_of"),
        SH.disjoint("head"),
    ] = Field(default=None)


class Contractor(Entity):
    pass


class DualIncome(Entity):
    pass


class Company(Entity):
    name: Annotated[str, SH.minLength(1), SH.maxLength(50)] = Field(
        description="Company name"
    )
    ceo: Annotated[
        Relation,
        SH.shclass("Manager"),
        SH.maxCount(1),
    ] = Field(description="Name of company CEO")


# Define ontology_model fixture to be used across test files
@pytest.fixture
def TestModel():

    onto = Pydontology(
        ontology=Person
        | Employee
        | Manager
        | Department
        | Company
        | Annotated[
            Contractor,
            OWL.equivalentClass(
                value=OWL.Restriction(
                    id="ContractorRestriction",
                    onProperty=Relation(id="has_contract_with"),
                    allValuesFrom=Relation(id="Company"),
                )
            ),
        ]
        | Annotated[DualIncome, OWL.intersectionOf(["Contractor", "Employee"])]
    )
    return onto


@pytest.fixture
def data_graph(TestModel):
    data_graph_model = TestModel.jsonld_graph()

    p1 = Person(
        id="Jane",
        name="Jane Doe",
        age=27,
        knows=Relation(id="John"),
    )
    p2 = Person(
        id="John", name="John Doe", age=45, has_contract_with=Relation(id="ACME")
    )
    e1 = Employee(
        id="JaneDoe",
        name="Jane Doe",
        employee_id="E000",
        age=27,
        sameAs=[Relation(id="Jane")],
        department=Relation(id="Accounting"),
        company=Relation(id="ACME"),
    )
    e2 = Employee(
        id="Mariella",
        name="Mariella Munez",
        employee_id="E001",
        differentFrom=Relation(id="JaneDoe"),
        department=Relation(id="Production"),
        company=Relation(id="ACME"),
    )
    m1 = Manager(
        id="Bud",
        name="Bud Weizer",
        employee_id="E002",
        department=Relation(id="Management"),
        company=Relation(id="EMCA"),
    )
    m2 = Manager(
        id="Rex",
        name="Rex Vega",
        employee_id="E003",
        department=Relation(id="Management"),
        company=Relation(id="ACME"),
    )

    c1 = Company(id="ACME", name="ACME", ceo=Relation(id="Rex"))
    c2 = Company(id="EMCA", name="EMCA", ceo=Relation(id="Bud"))

    data_graph = data_graph_model(graph=[p1, p2, e1, e2, m1, m2, c1, c2])

    return data_graph
