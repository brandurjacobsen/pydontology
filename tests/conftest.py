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
        """A person, subclass of Entity"""

        name: Annotated[
            str,
            SHACLAnnotation.minCount(1),
            SHACLAnnotation.minLength(1),
            SHACLAnnotation.maxLength(100),
        ] = Field(description="Person's name")
        age: Annotated[
            Optional[int],
            OWLAnnotation.functionalProperty(True),
            SHACLAnnotation.minInclusive(0),
            SHACLAnnotation.maxInclusive(150),
            SHACLAnnotation.datatype("xsd:integer"),
            SHACLAnnotation.severity("sh:Warning"),
        ] = Field(default=None, description="Person's age in years")
        knows: Annotated[Optional[Relation], OWLAnnotation.symmetricProperty(True)] = (
            Field(default=None, description="A friend or colleague")
        )

    class Employee(Person):
        """An employee, subclass of Person"""

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
            SHACLAnnotation.maxCount(1),
        ] = Field(default=None, description="Link to manager")

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

    class Manager(Employee):
        """A manager, subclass of Employee"""

        head_of: Annotated[
            Optional[Relation],
            RDFSAnnotation.range("Department"),
        ] = Field(default=None, description="Department manager heads")

        vice_head_of: Annotated[
            Optional[Relation],
            RDFSAnnotation.range("Department"),
        ] = Field(default=None, description="Department manager is vice head of")

    class Department(Entity):
        """A department, subclass of Entity"""

        name: Annotated[
            str, SHACLAnnotation.minLength(1), SHACLAnnotation.maxLength(50)
        ] = Field(description="Department's name")
        head: Annotated[
            Relation,
            RDFSAnnotation.range("Manager"),
            OWLAnnotation.inverseOf("head_of"),
            SHACLAnnotation.minCount(1),
            SHACLAnnotation.maxCount(1),
            SHACLAnnotation.disjoint("vice_head"),
        ]
        vice_head: Annotated[
            Optional[Relation],
            RDFSAnnotation.range("Manager"),
            OWLAnnotation.inverseOf("vice_head_of"),
            SHACLAnnotation.disjoint("head"),
        ] = Field(default=None)

    class Company(Entity):
        name: Annotated[
            str, SHACLAnnotation.minLength(1), SHACLAnnotation.maxLength(50)
        ] = Field(description="Company name")
        ceo: Annotated[Relation, SHACLAnnotation.shclass("Manager")] = Field(
            description="Name of CEO of company"
        )

    onto = Pydontology(ontology=Person | Employee | Manager | Department | Company)
    return onto
