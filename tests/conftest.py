from typing import Annotated, Optional

import pytest
from pydantic import Field

from pydontology.pydontology import (
    Entity,
    OWLAnnotation,
    Pydontology,
    RDFSAnnotation,
    Relation,
    SHACLAnnotation,
)


# Define ontology_model fixture to be used across test files
@pytest.fixture
def TestModel():
    class Person(Entity):
        """A person, inherits from Entity"""

        name: Annotated[
            str, SHACLAnnotation.minLength(1), SHACLAnnotation.maxLength(100)
        ] = Field(description="Person's name")
        age: Annotated[
            Optional[int],
            SHACLAnnotation.minInclusive(0),
            SHACLAnnotation.maxInclusive(150),
            SHACLAnnotation.severity("sh:Warning"),
        ] = Field(default=None, description="Person's age in years")
        knows: Optional[Relation] = Field(
            alias="foaf:knows", default=None, description="A friend or colleague"
        )

    class Employee(Person):
        """An employee, inherits from Person"""

        employee_id: Annotated[
            str,
            OWLAnnotation.functionalProperty(True),
            OWLAnnotation.inverseFunctionalProperty(True),
            SHACLAnnotation.pattern(r"^E\d{3}$"),
        ] = Field(description="Employee ID")

        manager: Annotated[
            Optional[Relation],
            RDFSAnnotation.range("Manager"),
            OWLAnnotation.transitiveProperty(True),
            SHACLAnnotation.shclass("Manager"),
            SHACLAnnotation.minCount(1),
        ] = Field(default=None, description="Link to manager")

    class Manager(Employee):
        """A manager, inherits from Employee"""

        manager: Optional[Relation] = Field(
            default=None, description="Manager of manager"
        )
        department: Annotated[
            Relation,
            RDFSAnnotation.range("Department"),
            SHACLAnnotation.minCount(1),
        ] = Field(description="Department IRI")
        company: Annotated[
            Relation,
            RDFSAnnotation.range("Company"),
            SHACLAnnotation.shclass("Company"),
        ]

    class Department(Entity):
        """A department, inherits from Entity"""

        name: Annotated[
            str, SHACLAnnotation.minLength(1), SHACLAnnotation.maxLength(50)
        ] = Field(description="Department's name")

    class Company(Entity):
        name: Annotated[
            str, SHACLAnnotation.minLength(1), SHACLAnnotation.maxLength(50)
        ] = Field(description="Company name")
        ceo: Annotated[Relation, SHACLAnnotation.shclass("Manager")] = Field(
            description="Name of CEO of company"
        )

    onto = Pydontology(ontology=Person | Employee | Manager | Department | Company)
    return onto
