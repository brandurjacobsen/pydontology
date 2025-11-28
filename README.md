# Pydontology
## Ontologies the Pydantic way

This package enables you to:

  * Build an RDF ontology using the well-known paradigms of Pydantic model classes.
  * Generate a JSON-LD (JSON for Linked Data) ontology graph from your ontology.
  * Generate a JSON-LD SHACL (Shapes Constraint Language) graph from your ontology.
  * Generate a JSON schema, which for example can be passed to LLMs to produce structured output.
  * Parse data adhering to the JSON schema directly, using e.g. *rdflib*.

When defining the classes in an ontology you can use typing.Annotated to provide RDFS/OWL and SHACL metadata to the attributes of the class.
Pydontology provides the functions: *ontology_graph* and *shacl_graph* to generate the ontology graph and shacl graph respectively as JSON-LD graphs.
This enables you to conceivably use SHACL constraints when validating LLM structured output, using e.g. pySHACL.


## Example 1
The package exposes, amongst others, the classes *Entity* and *Relation*, which inherit Pydantic's *BaseModel*.
Entity serves as the base class for ontology classes.
An attribute of an Entity class is considered to be an RDF literal, unless the attribute is of type *Relation*.

~~~
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
by using the *RDFSAnnotation.range* method.\
The [RDFS](https://www.w3.org/TR/rdf-schema/) domain is per default assumed to be the class wherein the attribute is defined.

The model can then be created using the *make_model* function:
~~~
from pydontology import make_model

ontology = Person | Employee | Manager
Model = make_model(ontology)
~~~

View the JSON schema, and the ontology in JSON-LD format:
~~~
import json
print(json.dumps(Model.model_json_schema(), indent=2)
print(Model.ontology_graph().dump_model_json(indent=2))
~~~
