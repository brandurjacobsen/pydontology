import marimo

__generated_with = "0.23.1"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    from typing import Annotated, List, Optional, get_origin

    from pydantic import Field

    from pydontology.pydontology import (
        Entity,
        Pydontology,
        RDFSAnnotation as RDFS,
        OWLAnnotation as OWL,
        Relation,
        SHACLAnnotation as SH,
        BaseContext
    )

    return (
        Annotated,
        BaseContext,
        Entity,
        Field,
        OWL,
        Optional,
        Pydontology,
        RDFS,
        Relation,
        SH,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    First we create an ontology using the Entity and Relation classes, and create an instance of the Pydontology class (Model) passing a union of the ontology classes an argument.
    """)
    return


@app.cell
def _(
    Annotated,
    Entity,
    Field,
    OWL,
    Optional,
    Pydontology,
    RDFS,
    Relation,
    SH,
):
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


    onto = Pydontology(Person | Employee | Manager)
    return Employee, Manager, Person, onto


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Create the json-ld ontology graph using `Model.ontology_graph` and serialize it as json
    """)
    return


@app.cell
def _(onto):
    ogj = onto.ontology_graph().model_dump_json(indent=2, exclude_none=True)

    print("Ontology graph JSON-LD:")
    print(ogj)
    return (ogj,)


@app.cell
def _(onto):
    sgj = onto.shacl_graph().model_dump_json(indent=2, exclude_none=True)
    print("SHACL graph JSON-LD:")
    print(sgj)
    return


@app.cell
def _(onto):
    import json
    schema = onto.jsonld_schema()
    print(json.dumps(schema.model_dump_json(), indent=2))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Parse the ontology graph in json-ld format using rdflib
    """)
    return


@app.cell(hide_code=True)
def _(ogj):
    from rdflib import Graph

    ontology_graph = Graph()

    ontology_graph.parse(data=ogj, format="json-ld")
    print("Ontology graph in Turtle format")
    print(ontology_graph.serialize(format="turtle"))
    return


@app.cell
def _():
    return


@app.cell
def _(BaseContext, Employee, Manager, Model, Person, Relation):
    p1 = Person(id="/person/p1", name="Joe", age=24)
    m1 = Manager(id="/manager/m1", name="Rex", employee_id="2", department="Sales")
    e1 = Employee(
        id="/employe/e1",
        name="Esmerelda",
        employee_id="1",
        has_manager=Relation(id="/manager/m1"),
    )

    dg = Model.jsonld_graph(
        context=BaseContext(vocab = "http://example.com/vocab/", base = "http://example.com/vocab"),
        graph=[p1, e1, m1],
    )

    print(dg.model_dump_json(indent=2))
    return


if __name__ == "__main__":
    app.run()
