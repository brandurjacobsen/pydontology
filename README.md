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
A field of an Entity class is considered to be an RDF literal, unless the attribute is of type Relation, 
in which case the value is interpreted as an IRI.
A field of type [LangStr] is serialized as an RDF language tagged literal, whose BCP47 language tag must be one of a fixed list of known tags.

Once the ontology classes are defined, an instance of the [Pydontology] class can be instantiated with the union of ontology classes as an argument.

Pydontology provides the methods: [ontology_graph] and [shacl_graph] to generate the ontology graph and shacl graph respectively, as a (populated) JSONLDGraph instance, ready for parsing by rdflib after serialization. The method [jsonld_graph] (backward-compatible alias: [schema_graph]) builds a Pydantic model of a JSON-LD data graph; its JSON schema (via `model_json_schema()`) can e.g. be passed to LLMs for structured output.

[Pydontology]: reference.md#pydontology.pydontology.Pydontology
[ontology_graph]: reference.md#pydontology.pydontology.Pydontology.ontology_graph
[shacl_graph]: reference.md#pydontology.pydontology.Pydontology.shacl_graph
[jsonld_graph]: reference.md#pydontology.pydontology.Pydontology.jsonld_graph
[schema_graph]: reference.md#pydontology.pydontology.Pydontology.schema_graph
[Entity]: reference.md#pydontology.pydontology.Entity
[Relation]: reference.md#pydontology.pydontology.Relation
[LangStr]: reference.md#pydontology.pydontology.LangStr
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

## Documentation
Documentation is built using mkdocs and hosted using Github Pages here: [https://brandurjacobsen.github.io/pydontology/](https://brandurjacobsen.github.io/pydontology/)


## Example

~~~
from typing import Annotated, Optional

from pydantic import Field

from pydontology import (
    BaseContext,
    Entity,
    Relation,
    Settings,
    Pydontology,
    RDFSAnnotation as RDFS,
    OWLAnnotation as OWL,
    SHACLAnnotation as SH,

)

class Person(Entity):
    """A person class"""
    name: str = Field(description="Person's name")
    age: Annotated[Optional[int], OWL.functionalProperty(True)] = Field(default=None, description="Person's age")


class Employee(Person):
    """An employee class, inherits from Person"""
    employee_id: Annotated[
      str,
      OWL.functionalProperty(True),
      OWL.inverseFunctionalProperty(True),
      SH.minCount(1),
      SH.maxCount(1)] = Field(description="Employee ID")

    has_manager: Annotated[
      Optional[Relation], 
      RDFS.range("Manager"),
      SH.shclass("Manager")] = Field(default=None, description="Link to manager")

    department: Annotated[Relation, RDFS.range("Department")] = Field(description="Link to department")

class Worker(Person):
    pass

class Manager(Employee):
    """A manager class, inherits from Employee"""
    heads: Annotated[Relation | None, RDFS.range("Department")] = Field(default=None, description="Department that manager heads")

class Department(Entity):
    """A department class"""
    # Name property is defined again with same Python type
    name: Annotated[str, RDFS.comment("Person or department name")] = Field(description="Name of department")  
    
ontology = Person | Annotated[Employee, OWL.equivalentClass("Worker")] | Manager | Department

~~~

Note the use of typing.Annotated above to annotate properties and Entity classes with RDFS, OWL constructs.
These will appear in the ontology graph and SHACL graph.

Inherited ontology classes will per default have RDFS subClassOf property set to be the parent class, or owl:Thing class if inheriting from Entity(multiple inheritance is currently not implemented when defining classes, but can be achieved by annotating the inherited class after the definition).

The RDFS domain of an ontology property is per default set to be the class wherein the property is defined, unless the property is defined in multiple ontology classes, in which case the user will receive a UserWarning.

The default annotation behaviour (and whether to show warnings) can be controlled via the [Settings] class, which [ontology_graph] and [shacl_graph] accept as an optional parameter.

Note that [ontology_graph], [shacl_graph], and [jsonld_graph] accept an optional `context` parameter (a [BaseContext]). By default no `@vocab` or `@base` is emitted in the JSON-LD `@context`. Relative names (class names, property names, annotation values) are qualified using the compact prefix from `Settings.DEFAULT_PREFIX` (default `"ex:"`), so class and property ids are emitted as e.g. `ex:Person`. Set `Settings.DEFAULT_PREFIX_NS` to the namespace IRI behind that prefix and Pydontology injects the corresponding mapping (e.g. `"ex": "http://example.com/vocab/"`) into the emitted `@context`, so consumers such as rdflib expand the compact IRIs. To deliberately keep bare relative names, set `DEFAULT_PREFIX=None`, in which case every property must carry an explicit `serialization_alias` or IRI.

The model can then be created by instantiating the [Pydontology] class with the ontology,
and the ontology graph and SHACL graph can be created using the [ontology_graph] and [shacl_graph] methods.
A JSON schema for a JSON-LD data graph is obtained from the [jsonld_graph] model via Pydantic's `model_json_schema()` (see below).
~~~
import json

pydonto = Pydontology(ontology)

# Declare the namespace behind the "ex:" prefix so @context can expand it
context = BaseContext(vocab="http://example.com/vocab/", base="http://example.com/vocab/")
settings = Settings(DEFAULT_PREFIX_NS="http://example.com/vocab/")

ontog = pydonto.ontology_graph(context=context, settings=settings)
ontog_json = ontog.model_dump_json(indent=2, exclude_none=True)

shaclg = pydonto.shacl_graph(context=context, settings=settings)
shaclg_json = shaclg.model_dump_json(indent=2, exclude_none=True)

schemag = pydonto.jsonld_graph()  # schema_graph() is a backward-compatible alias
schemag_json = json.dumps(schemag.model_json_schema(), indent=2)
~~~

Output of `print(ontog_json)`:

~~~
{
  "@context": {
    "@version": 1.1,
    "@vocab": "http://example.com/vocab/",
    "@base": "http://example.com/vocab/",
    "sh": "http://www.w3.org/ns/shacl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "ex": "http://example.com/vocab/"
  },
  "@graph": [
    {
      "@id": "ex:Person",
      "@type": "rdfs:Class",
      "rdfs:label": "Person",
      "rdfs:comment": "A person class",
      "rdfs:subClassOf": [
        {
          "@id": "owl:Thing"
        }
      ]
    },
    {
      "@id": "ex:Employee",
      "@type": "rdfs:Class",
      "rdfs:label": "Employee",
      "rdfs:comment": "An employee class, inherits from Person",
      "rdfs:subClassOf": [
        {
          "@id": "ex:Person"
        }
      ],
      "owl:equivalentClass": [
        {
          "@id": "ex:Worker"
        }
      ]
    },
    {
      "@id": "ex:Manager",
      "@type": "rdfs:Class",
      "rdfs:label": "Manager",
      "rdfs:comment": "A manager class, inherits from Employee",
      "rdfs:subClassOf": [
        {
          "@id": "ex:Employee"
        }
      ]
    },
    {
      "@id": "ex:Department",
      "@type": "rdfs:Class",
      "rdfs:label": "Department",
      "rdfs:comment": "A department class",
      "rdfs:subClassOf": [
        {
          "@id": "owl:Thing"
        }
      ]
    },
    {
      "@id": "ex:name",
      "@type": [
        "owl:DatatypeProperty",
        "xsd:string"
      ],
      "rdfs:label": "name",
      "rdfs:comment": "Person or department name"
    },
    {
      "@id": "ex:age",
      "@type": [
        "owl:DatatypeProperty",
        "xsd:integer",
        "owl:FunctionalProperty"
      ],
      "rdfs:label": "age",
      "rdfs:domain": {
        "@id": "ex:Person"
      },
      "rdfs:comment": "Person's age"
    },
    {
      "@id": "ex:employee_id",
      "@type": [
        "owl:DatatypeProperty",
        "xsd:string",
        "owl:FunctionalProperty",
        "owl:InverseFunctionalProperty"
      ],
      "rdfs:label": "employee_id",
      "rdfs:domain": {
        "@id": "ex:Employee"
      },
      "rdfs:comment": "Employee ID"
    },
    {
      "@id": "ex:has_manager",
      "@type": [
        "owl:ObjectProperty"
      ],
      "rdfs:label": "has_manager",
      "rdfs:domain": {
        "@id": "ex:Employee"
      },
      "rdfs:range": {
        "@id": "ex:Manager"
      },
      "rdfs:comment": "Link to manager"
    },
    {
      "@id": "ex:department",
      "@type": [
        "owl:ObjectProperty"
      ],
      "rdfs:label": "department",
      "rdfs:domain": {
        "@id": "ex:Employee"
      },
      "rdfs:range": {
        "@id": "ex:Department"
      },
      "rdfs:comment": "Link to department"
    },
    {
      "@id": "ex:heads",
      "@type": [
        "owl:ObjectProperty"
      ],
      "rdfs:label": "heads",
      "rdfs:domain": {
        "@id": "ex:Manager"
      },
      "rdfs:range": {
        "@id": "ex:Department"
      },
      "rdfs:comment": "Department that manager heads"
    }
  ]
}
~~~

Output of `print(shaclg_json)`:

~~~
{
  "@context": {
    "@version": 1.1,
    "@vocab": "http://example.com/vocab/",
    "@base": "http://example.com/vocab/",
    "sh": "http://www.w3.org/ns/shacl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "ex": "http://example.com/vocab/"
  },
  "@graph": [
    {
      "@id": "ex:PersonShape",
      "@type": "sh:NodeShape",
      "sh:targetClass": {
        "@id": "ex:Person"
      },
      "sh:property": [
        {
          "@id": "ex:PersonShape_name",
          "@type": "sh:PropertyShape",
          "sh:path": {
            "@id": "ex:name"
          },
          "sh:datatype": {
            "@id": "xsd:string"
          },
          "sh:name": "name",
          "sh:description": "Person's name"
        },
        {
          "@id": "ex:PersonShape_age",
          "@type": "sh:PropertyShape",
          "sh:path": {
            "@id": "ex:age"
          },
          "sh:datatype": {
            "@id": "xsd:integer"
          },
          "sh:name": "age",
          "sh:description": "Person's age"
        }
      ]
    },
    {
      "@id": "ex:EmployeeShape",
      "@type": "sh:NodeShape",
      "sh:targetClass": {
        "@id": "ex:Employee"
      },
      "sh:property": [
        {
          "@id": "ex:EmployeeShape_employee_id",
          "@type": "sh:PropertyShape",
          "sh:path": {
            "@id": "ex:employee_id"
          },
          "sh:datatype": {
            "@id": "xsd:string"
          },
          "sh:minCount": 1,
          "sh:maxCount": 1,
          "sh:name": "employee_id",
          "sh:description": "Employee ID"
        },
        {
          "@id": "ex:EmployeeShape_has_manager",
          "@type": "sh:PropertyShape",
          "sh:path": {
            "@id": "ex:has_manager"
          },
          "sh:class": {
            "@id": "ex:Manager"
          },
          "sh:nodeKind": {
            "@id": "sh:IRI"
          },
          "sh:name": "has_manager",
          "sh:description": "Link to manager"
        },
        {
          "@id": "ex:EmployeeShape_department",
          "@type": "sh:PropertyShape",
          "sh:path": {
            "@id": "ex:department"
          },
          "sh:nodeKind": {
            "@id": "sh:IRI"
          },
          "sh:name": "department",
          "sh:description": "Link to department"
        }
      ]
    },
    {
      "@id": "ex:ManagerShape",
      "@type": "sh:NodeShape",
      "sh:targetClass": {
        "@id": "ex:Manager"
      },
      "sh:property": [
        {
          "@id": "ex:ManagerShape_heads",
          "@type": "sh:PropertyShape",
          "sh:path": {
            "@id": "ex:heads"
          },
          "sh:nodeKind": {
            "@id": "sh:IRI"
          },
          "sh:name": "heads",
          "sh:description": "Department that manager heads"
        }
      ]
    },
    {
      "@id": "ex:DepartmentShape",
      "@type": "sh:NodeShape",
      "sh:targetClass": {
        "@id": "ex:Department"
      },
      "sh:property": [
        {
          "@id": "ex:DepartmentShape_name",
          "@type": "sh:PropertyShape",
          "sh:path": {
            "@id": "ex:name"
          },
          "sh:datatype": {
            "@id": "xsd:string"
          },
          "sh:name": "name",
          "sh:description": "Name of department"
        }
      ]
    }
  ]
}
~~~

Output of `print(schemag_json)`:

~~~
{
  "$defs": {
    "BaseContext": {
      "description": "Base json-ld context model",
      "properties": {
        "version": {
          "default": 1.1,
          "title": "Version",
          "type": "number"
        },
        "vocab": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Prefix of properties, values of @type, and values of terms that are relative. Defaults to None, in which case relative IRIs in the document are left unresolved and consumers must supply a base or use absolute IRIs.",
          "title": "Vocab"
        },
        "base": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Prefix of relative IRIs. Defaults to None, in which case relative IRIs in the document are left unresolved and consumers must supply a base or use absolute IRIs.",
          "title": "Base"
        },
        "language": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "BCP47 default language identifier",
          "title": "Language"
        },
        "sh": {
          "const": "http://www.w3.org/ns/shacl#",
          "default": "http://www.w3.org/ns/shacl#",
          "title": "Sh",
          "type": "string"
        },
        "xsd": {
          "const": "http://www.w3.org/2001/XMLSchema#",
          "default": "http://www.w3.org/2001/XMLSchema#",
          "title": "Xsd",
          "type": "string"
        },
        "rdfs": {
          "const": "http://www.w3.org/2000/01/rdf-schema#",
          "default": "http://www.w3.org/2000/01/rdf-schema#",
          "title": "Rdfs",
          "type": "string"
        },
        "owl": {
          "const": "http://www.w3.org/2002/07/owl#",
          "default": "http://www.w3.org/2002/07/owl#",
          "title": "Owl",
          "type": "string"
        },
        "prefixes": {
          "additionalProperties": {
            "type": "string"
          },
          "description": "Additional JSON-LD prefix mappings merged into @context",
          "title": "Prefixes",
          "type": "object"
        }
      },
      "title": "BaseContext",
      "type": "object"
    },
    "Department": {
      "description": "A department class",
      "properties": {
        "id": {
          "description": "IRI",
          "minLength": 1,
          "title": "@id",
          "type": "string"
        },
        "sameAs": {
          "anyOf": [
            {
              "$ref": "#/$defs/Relation"
            },
            {
              "items": {
                "$ref": "#/$defs/Relation"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Same individual(s)",
          "title": "Sameas"
        },
        "differentFrom": {
          "anyOf": [
            {
              "$ref": "#/$defs/Relation"
            },
            {
              "items": {
                "$ref": "#/$defs/Relation"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Different individual(s)",
          "title": "Differentfrom"
        },
        "name": {
          "description": "Name of department",
          "title": "Name",
          "type": "string"
        }
      },
      "required": [
        "id",
        "name"
      ],
      "title": "Department",
      "type": "object"
    },
    "Employee": {
      "description": "An employee class, inherits from Person",
      "properties": {
        "id": {
          "description": "IRI",
          "minLength": 1,
          "title": "@id",
          "type": "string"
        },
        "sameAs": {
          "anyOf": [
            {
              "$ref": "#/$defs/Relation"
            },
            {
              "items": {
                "$ref": "#/$defs/Relation"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Same individual(s)",
          "title": "Sameas"
        },
        "differentFrom": {
          "anyOf": [
            {
              "$ref": "#/$defs/Relation"
            },
            {
              "items": {
                "$ref": "#/$defs/Relation"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Different individual(s)",
          "title": "Differentfrom"
        },
        "name": {
          "description": "Person's name",
          "title": "Name",
          "type": "string"
        },
        "age": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Person's age",
          "title": "Age"
        },
        "employee_id": {
          "description": "Employee ID",
          "title": "Employee Id",
          "type": "string"
        },
        "has_manager": {
          "anyOf": [
            {
              "$ref": "#/$defs/Relation"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Link to manager"
        },
        "department": {
          "$ref": "#/$defs/Relation",
          "description": "Link to department"
        }
      },
      "required": [
        "id",
        "name",
        "employee_id",
        "department"
      ],
      "title": "Employee",
      "type": "object"
    },
    "Manager": {
      "description": "A manager class, inherits from Employee",
      "properties": {
        "id": {
          "description": "IRI",
          "minLength": 1,
          "title": "@id",
          "type": "string"
        },
        "sameAs": {
          "anyOf": [
            {
              "$ref": "#/$defs/Relation"
            },
            {
              "items": {
                "$ref": "#/$defs/Relation"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Same individual(s)",
          "title": "Sameas"
        },
        "differentFrom": {
          "anyOf": [
            {
              "$ref": "#/$defs/Relation"
            },
            {
              "items": {
                "$ref": "#/$defs/Relation"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Different individual(s)",
          "title": "Differentfrom"
        },
        "name": {
          "description": "Person's name",
          "title": "Name",
          "type": "string"
        },
        "age": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Person's age",
          "title": "Age"
        },
        "employee_id": {
          "description": "Employee ID",
          "title": "Employee Id",
          "type": "string"
        },
        "has_manager": {
          "anyOf": [
            {
              "$ref": "#/$defs/Relation"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Link to manager"
        },
        "department": {
          "$ref": "#/$defs/Relation",
          "description": "Link to department"
        },
        "heads": {
          "anyOf": [
            {
              "$ref": "#/$defs/Relation"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Department that manager heads"
        }
      },
      "required": [
        "id",
        "name",
        "employee_id",
        "department"
      ],
      "title": "Manager",
      "type": "object"
    },
    "Person": {
      "description": "A person class",
      "properties": {
        "id": {
          "description": "IRI",
          "minLength": 1,
          "title": "@id",
          "type": "string"
        },
        "sameAs": {
          "anyOf": [
            {
              "$ref": "#/$defs/Relation"
            },
            {
              "items": {
                "$ref": "#/$defs/Relation"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Same individual(s)",
          "title": "Sameas"
        },
        "differentFrom": {
          "anyOf": [
            {
              "$ref": "#/$defs/Relation"
            },
            {
              "items": {
                "$ref": "#/$defs/Relation"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Different individual(s)",
          "title": "Differentfrom"
        },
        "name": {
          "description": "Person's name",
          "title": "Name",
          "type": "string"
        },
        "age": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Person's age",
          "title": "Age"
        }
      },
      "required": [
        "id",
        "name"
      ],
      "title": "Person",
      "type": "object"
    },
    "Relation": {
      "description": "A relation is a reference to an IRI",
      "properties": {
        "id": {
          "description": "IRI",
          "title": "@id",
          "type": "string"
        }
      },
      "required": [
        "id"
      ],
      "title": "Relation",
      "type": "object"
    }
  },
  "properties": {
    "context": {
      "$ref": "#/$defs/BaseContext",
      "default": {
        "@version": 1.1,
        "sh": "http://www.w3.org/ns/shacl#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "owl": "http://www.w3.org/2002/07/owl#"
      },
      "description": "JSON-LD context",
      "name": "@context"
    },
    "id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Optional IRI of the graph",
      "title": "Id"
    },
    "graph": {
      "description": "Default json-ld graph",
      "items": {
        "anyOf": [
          {
            "$ref": "#/$defs/Person"
          },
          {
            "$ref": "#/$defs/Employee"
          },
          {
            "$ref": "#/$defs/Manager"
          },
          {
            "$ref": "#/$defs/Department"
          }
        ]
      },
      "name": "@graph",
      "title": "Graph",
      "type": "array"
    }
  },
  "required": [
    "graph"
  ],
  "title": "PydontologyModel",
  "type": "object"
}
~~~

These outputs can be parsed by rdflib into a graph and serialized into e.g. Turtle format.

More on will be said on this here later.
