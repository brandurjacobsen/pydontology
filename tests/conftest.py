from typing import Annotated, Optional

import pytest
from pydantic import Field

from pydontology import Entity, RDFSAnnotation, Relation, make_model


# Define ontology_model fixture to be used across test files
@pytest.fixture
def ontology_model():
    class Person(Entity):
        """A person"""

        name: str = Field(description="Person's name")
        age: Optional[int] = Field(default=None, description="Person's age")

    class Employee(Person):
        """An employee, inherits from Person"""

        employee_id: str = Field(description="Employee ID")
        manager: Annotated[Optional[Relation], RDFSAnnotation.range("Manager")] = Field(
            default=None, description="Link to manager"
        )

    class Manager(Employee):
        """A manager, inherits from Employee"""

        department: Annotated[
            Optional[Relation], RDFSAnnotation.range("Department")
        ] = Field(default=None, description="Department IRI")

    class Department(Entity):
        """A department, inherits from Entity"""

        name: str = Field(description="Department name")

    return make_model(Person | Employee | Manager | Department, "TestModel")
