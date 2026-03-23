import marimo

__generated_with = "0.21.0"
app = marimo.App(width="full")


@app.cell
def _():
    from typing import Annotated, List, Optional

    from pydantic import Field

    from pydontology.pydontology import (
        Entity,
        Pydontology,
        RDFSAnnotation,
        Relation,
        SHACLAnnotation,
    )

    return (
        Annotated,
        Entity,
        Field,
        Optional,
        Pydontology,
        RDFSAnnotation,
        Relation,
    )


@app.cell
def _(
    Annotated,
    Entity,
    Field,
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

        employee_id: str = Field(description="Employee ID")
        has_manager: Annotated[
            Optional[Relation],
            RDFSAnnotation.range("Manager"),
        ] = Field(default=None, description="Link to manager")

    class Manager(Employee):
        """A manager entity, inherits from Employee"""

        department: str = Field(description="Department name")

    ontology = Person | Employee | Manager
    Model = Pydontology(ontology)
    print(Model.ontology_graph().model_dump_json(indent=2, exclude_none=True))
    return Employee, Manager, Model, Person


@app.cell
def _(Employee, Manager, Model, Person, Relation):
    p1 = Person(id="/person/p1", name="Joe", age=24)
    m1 = Manager(id="/manager/m1", name="Rex", employee_id="2", department="Sales")
    e1 = Employee(
        id="/employe/e1",
        name="Esmerelda",
        employee_id="1",
        has_manager=Relation(id="/manager/m1"),
    )

    dg = Model.jsonld_graph(
        context={
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/",
            "sh": "http://www.w3.org/ns/shacl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        graph=[p1, e1, m1],
    )
    dgj = dg.model_dump_json(indent=2, exclude_none=True)

    ogj = Model.ontology_graph().model_dump_json(indent=2, exclude_none=True)

    sgj = Model.shacl_graph().model_dump_json(indent=2, exclude_none=True)

    print("Data graph JSON-LD:")
    print(dgj)

    print("Ontology graph JSON-LD:")
    print(ogj)

    print("SHACL graph JSON-LD:")
    print(sgj)
    return dgj, ogj, sgj


@app.cell(hide_code=True)
def _(dgj, ogj, sgj):
    from rdflib import Graph

    data_graph = Graph()
    ontology_graph = Graph()
    shacl_graph = Graph()

    data_graph.parse(data=dgj, format="json-ld")
    ontology_graph.parse(data=ogj, format="json-ld")
    shacl_graph.parse(data=sgj, format="json-ld")

    print("Data graph in turtle format:")
    print(data_graph.serialize(format="turtle"))

    print("Ontology graph in turtle format")
    print(ontology_graph.serialize(format="turtle"))

    print("SHACL graph in turtle format")
    print(shacl_graph.serialize(format="turtle"))
    return data_graph, ontology_graph, shacl_graph


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
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
 
    """)
    return


if __name__ == "__main__":
    app.run()
