import marimo

__generated_with = "0.23.1"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
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
def _(Annotated, Entity, Field, OWL, Optional, RDFS, Relation, SH):
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
    return Employee, Manager, Person, ontology


@app.cell
def _(Pydontology, ontology):
    pydonto = Pydontology(ontology)
    onto_graph = pydonto.ontology_graph()
    sh_graph = pydonto.shacl_graph()
    return onto_graph, sh_graph


@app.cell
def _(onto_graph):
    print(onto_graph.model_dump_json(indent=2, exclude_none=True))
    return


@app.cell
def _(sh_graph):
    print(sh_graph.model_dump_json(indent=2, exclude_none=True))

    return


@app.cell
def _(onto):
    import json
    model = onto.make_model()
    print(json.dumps(model.model_json_schema(), indent=2))
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
