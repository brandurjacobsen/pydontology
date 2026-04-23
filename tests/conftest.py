from typing import Annotated, Optional

import pytest
from pydantic import Field

from pydontology.pydontology import (
    Entity,
    Pydontology,
    Relation,
)
from pydontology.pydontology import (
    OWLAnnotation as OWL,
)
from pydontology.pydontology import (
    RDFSAnnotation as RDFS,
)
from pydontology.pydontology import (
    SHACLAnnotation as SH,
)


# Define ontology_model fixture to be used across test files
@pytest.fixture
def TestModel():
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
        knows: Annotated[Optional[Relation], OWL.symmetricProperty(True)] = Field(
            default=None, description="A friend or colleague"
        )

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

    class Company(Entity):
        name: Annotated[str, SH.minLength(1), SH.maxLength(50)] = Field(
            description="Company name"
        )
        ceo: Annotated[Relation, SH.shclass("Manager")] = Field(
            description="Name of company CEO"
        )

    onto = Pydontology(ontology=Person | Employee | Manager | Department | Company)
    return onto
