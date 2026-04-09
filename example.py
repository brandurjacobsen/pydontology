import marimo

__generated_with = "0.21.0"
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
        RDFSAnnotation,
        OWLAnnotation,
        Relation,
        SHACLAnnotation,
        BaseContext
    )

    return (
        Annotated,
        BaseContext,
        Entity,
        Field,
        OWLAnnotation,
        Optional,
        Pydontology,
        RDFSAnnotation,
        Relation,
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
    OWLAnnotation,
    Optional,
    Pydontology,
    RDFSAnnotation,
    Relation,
):
    class Person(Entity):
        """A person entity"""

        name: str = Field(description="Person's name")
        age: Optional[int] = Field(default=None, description="Person's age")

    class Employee(Person):
        """An employee entity, inherits from Person"""

        employee_id: Annotated[str, OWLAnnotation.functionalProperty(True)] = Field(description="Employee ID")
        has_manager: Annotated[
            Optional[Relation],
            RDFSAnnotation.range("Manager"),
        ] = Field(default=None, description="Link to manager")

    class Worker(Person):
        pass

    class Manager(Employee):
        """A manager entity, inherits from Employee"""

        department: Annotated[Relation, RDFSAnnotation.range("Department")] = Field(description="Link to department")

    class Department(Entity):
        """Department entity, inherits Relation"""
        dept_name: str = Field(description="Department name")

    ontology = Person | Annotated[Employee, OWLAnnotation.equivalentClass("Worker")] | Worker | Manager | Department
    Model = Pydontology(ontology)
    return Employee, Manager, Model, Person


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Create the json-ld ontology graph using `Model.ontology_graph` and serialize it as json
    """)
    return


@app.cell
def _(Model):
    ogj = Model.ontology_graph().model_dump_json(indent=2, exclude_none=True)

    print("Ontology graph JSON-LD:")
    print(ogj)

    sgj = Model.shacl_graph().model_dump_json(indent=2, exclude_none=True)
    print("SHACL graph JSON-LD:")
    print(sgj)
    return (ogj,)


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
    return (ontology_graph,)


@app.cell
def _(data_graph, ontology_graph, shacl_graph):
    from pyshacl import validate

    r = validate(
        data_graph,
        shacl_graph=shacl_graph,
        ont_graph=ontology_graph,
        inference="rdfs",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
        meta_shacl=False,
        advanced=False,
        js=False,
        debug=False,
    )
    conforms, results_graph, results_text = r
    print(conforms)
    print(results_graph)
    print(results_text)
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
