# Pydontology
## Ontologies the Pydantic way

This package enables you to:

  * Build an RDF ontology using the well-known Pydantic model classes
  * Use typing.Annotated to add RDFS/OWL and SHACL metadata to your ontology class attributes
  * Generate a JSON-LD (JSON for Linked Data) ontology graph from your ontology and metadata
  * Generate a JSON-LD SHACL (Shapes Constraint Language) graph from your ontology and metadata
  * Generate a JSON schema, which for example can be passed to LLMs to produce structured output
  * Parse data adhering to the JSON schema directly, using e.g. rdflib

The package exposes, amongst others, the classes *Entity* and *Relation*, which inherit Pydantic's BaseModel.
Entity serves as the base class for ontology classes.
An attribute of an Entity class is considered to be an RDF literal, unless the attribute is of type Relation.

Once the ontology classes are defined, a call to *make_model* will return a *JSONLDGraph* class
that, once instantiated and populated with ontology 'individuals', will serialize as a valid JSON-LD document, ready for parsing by e.g. rdflib.

JSONLDGraph provides the class methods: *ontology_graph* and *shacl_graph* to generate the ontology graph and shacl graph respectively, as a (populated) JSONLDGraph instance.

## Installation
This package is currently distributed via TestPyPi. 

To install in a Python virtual environment, run the following commands in a terminal, in a directory of your chosing: 
~~~
# Replace <venv_name> with a sensible name for the virtual environment
python3 -m venv <venv_name>  
source <venv_name>/bin/activate
pip install --upgrade pip  # Optional
pip install pydantic  # Required
pip install -i https://test.pypi.org/simple/ pydontology
~~~


## Example 1

~~~
from pydantic import Field
from typing import Optional, Annotated
from pydontology import Entity, Relation, RDFSAnnotation

class Person(Entity):
    """A person entity"""
    name: str = Field(description="Person's name")
    age: Optional[int] = Field(default=None, description="Person's age")


class Employee(Person):
    """An employee entity, inherits from Person"""
    employee_id: str = Field(description="Employee ID")
    has_manager: Annotated[Optional[Relation], RDFSAnnotation.range('Manager')] = Field(default=None, description="Link to manager")


class Manager(Employee):
    """A manager entity, inherits from Employee"""
    department: str = Field(description="Department name")
~~~

Note the use of typing.Annotated above to have the ontology graph include the triple: `ex:has_manager rdfs:range ex:Manager`,
by using the *RDFSAnnotation.range* method.
The RDFS domain is per default assumed to be the class wherein the attribute is defined.

The model can then be created using the *make_model* function:
~~~
from pydontology import make_model

ontology = Person | Employee | Manager
Model = make_model(ontology)
~~~

View the JSON schema, and the ontology in JSON-LD format:
~~~
import json
print(json.dumps(Model.model_json_schema(), indent=2))
print(Model.ontology_graph().model_dump_json(indent=2))
~~~
