from typing import Annotated, Optional

import pytest
from pydantic import Field

from pydontology import Entity, RDFSAnnotation, Relation, SHACLAnnotation, make_model


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
        ] = Field(default=None, description="Person's age")

    class Employee(Person):
        """An employee, inherits from Person"""

        employee_id: Annotated[str, SHACLAnnotation.pattern(r"^E\d{3}$")] = Field(
            description="Employee ID"
        )
        manager: Annotated[
            Optional[Relation],
            RDFSAnnotation.range("Manager"),
            SHACLAnnotation.shclass("Manager"),
            SHACLAnnotation.maxCount(1),
        ] = Field(default=None, description="Link to manager")

    class Manager(Employee):
        """A manager, inherits from Employee"""

        department: Annotated[
            Optional[Relation],
            RDFSAnnotation.range("Department"),
            SHACLAnnotation.minLength(1),
        ] = Field(default=None, description="Department IRI")

    class Department(Entity):
        """A department, inherits from Entity"""

        name: str = Field(description="Department name")

    return make_model(
        ontology=Person | Employee | Manager | Department, name="TestModel"
    )
