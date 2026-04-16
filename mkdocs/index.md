# Pydontology
## _Ontologies the Pydantic way_

This package will enable you to:

  * Build an RDF ontology using the well-known Pydantic model classes
  * Use typing.Annotated to add RDFS/OWL and SHACL metadata to your ontology class properties
  * Generate a JSON-LD (JSON for Linked Data) ontology graph from your ontology and metadata
  * Generate a JSON-LD SHACL (Shapes Constraint Language) graph from your ontology and metadata
  * Generate a JSON schema from your ontology, which for example can be passed to LLMs to produce structured output
  * Parse data adhering to the JSON schema directly, using e.g. rdflib

The package exposes, amongst others, the classes [Entity] and [Relation], which inherit Pydantic's BaseModel.
Entity serves as the base class for ontology classes.
An attribute of an Entity class is considered to be an RDF literal, unless the attribute is of type Relation, 
in which case the value is interpreted as an IRI.

Once the ontology classes are defined, an instance of the [Pydontology] class can be instantiated with the union of ontology classes as an argument.

Pydontology provides the methods: [ontology_graph] and [shacl_graph] to generate the ontology graph and shacl graph respectively, as a (populated) JSONLDGraph instance, ready for parsing by rdflib after serialization.

[Pydontology]: reference.md#pydontology.pydontology.Pydontology
[ontology_graph]: reference.md#pydontology.pydontology.Pydontology.ontology_graph
[shacl_graph]: reference.md#pydontology.pydontology.Pydontology.shacl_graph
[Entity]: reference.md#pydontology.pydontology.Entity
[Relation]: reference.md#pydontology.pydontology.Relation
[Settings]: reference.md#pydontology.settings.Settings

[RDFSAnnotation.range]: reference.md#pydontology.rdfs.RDFSAnnotation.range

## Installation
This package is currently distributed via [TestPyPi](https://test.pypi.org/project/pydontology/). 

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
from pydontology import (
  Pydontology, 
  Entity, 
  Relation, 
  RDFSAnnotation as RDFS, 
  OWLAnnotation as OWL, 
  SHACLAnnotation as SH
)

class Person(Entity):
    """A person entity"""
    name: str = Field(description="Person's name")
    age: Optional[int] = Field(default=None, description="Person's age")


class Employee(Person):
    """An employee entity, inherits from Person"""
    employee_id: Annotated[
      str,
      OWL.functionalProperty(True),
      OWL.inverseFunctionalProperty(True),
      SH.minCount(1),
      SH.maxCount(1)] = Field(description="Employee ID")
    has_manager: Annotated[
      Optional[Relation], 
      RDFS.range('Manager')] = Field(default=None, description="Link to manager")


class Manager(Employee):
    """A manager entity, inherits from Employee"""
    department: str = Field(description="Department name")
~~~

Note the use of typing.Annotated above to have the ontology graph include the triple: `ex:has_manager rdfs:range ex:Manager`,
by using the [RDFSAnnotation.range] method.

The RDFS domain is per default set to be the class wherein the property is defined, unless the property is defined in multiple ontology classes.
This behaviour can be controlled via the [Settings] class, which [ontology_graph] and [shacl_graph] accept as an optional parameter.

The model can then be created by instantiating the [Pydontology] class with the ontology:
~~~
from pydontology import Pydontology

ontology = Person | Employee | Manager
Model = Pydontology(ontology)
~~~

View the JSON schema, and the ontology in JSON-LD format:
~~~
import json
print(json.dumps(Model.model_json_schema(), indent=2))
print(Model.ontology_graph().model_dump_json(indent=2))
~~~
