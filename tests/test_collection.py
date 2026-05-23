import pytest

from pydontology.collection import PydontologyCollection
from pydontology.models import BaseMetaData, Entity, JSONLDGraph, Relation
from pydontology.pydontology import Pydontology


def test_collection_tool_outputs(TestModel):
    pytest.importorskip("pydantic_ai.output")
    from pydantic_ai.output import ToolOutput

    collection = PydontologyCollection()
    collection.register(
        name="people",
        ontology=TestModel,
        description="Person and organization ontology",
    )

    outputs = collection.tool_outputs()

    assert len(outputs) == 1
    assert isinstance(outputs[0], ToolOutput)
    assert outputs[0].name == "people"
    print("ToolOutput description:")
    print(outputs[0].description)
    assert str("Person and organization ontology") in outputs[0].description
    assert str("Associated owl:Ontology") in outputs[0].description


def test_collection_ontology_graph_union(TestModel):
    class Animal(Entity):
        """Animal entity."""

        animal_name: str

    class Pet(Entity):
        """Pet entity."""

        pet_owner: Relation

    animal_ontology = Pydontology(
        Animal | Pet,
        BaseMetaData(id="AnimalOntology", comment="Animal ontology"),
    )

    collection = PydontologyCollection(
        metadata=BaseMetaData(id="CollectionOntology", comment="Collection ontology")
    )
    collection.register(
        name="people",
        ontology=TestModel,
        description="Person and organization ontology",
    )
    collection.register(
        name="animals",
        ontology=animal_ontology,
        description="Animal ontology",
    )

    graph = collection.ontology_graph()

    assert isinstance(graph, JSONLDGraph)

    graph_ids = {
        item.model_dump(by_alias=True, exclude_none=True).get("@id")
        for item in graph.graph
        if hasattr(item, "model_dump")
    }
    assert "Person" in graph_ids
    assert "Animal" in graph_ids

    ontology_nodes = [
        item
        for item in graph.graph
        if hasattr(item, "model_dump")
        and item.model_dump(by_alias=True, exclude_none=True).get("@type")
        == "owl:Ontology"
    ]
    ontology_ids = {
        item.model_dump(by_alias=True, exclude_none=True).get("@id")
        for item in ontology_nodes
    }
    assert "TestOntology" in ontology_ids
    assert "AnimalOntology" in ontology_ids
    assert "CollectionOntology" in ontology_ids

    collection_ontology = next(
        item
        for item in ontology_nodes
        if item.model_dump(by_alias=True, exclude_none=True).get("@id")
        == "CollectionOntology"
    )
    imports = collection_ontology.model_dump(by_alias=True, exclude_none=True).get(
        "owl:imports"
    )
    import_ids = [item["@id"] for item in imports]
    assert import_ids == ["TestOntology", "AnimalOntology"]


def test_collection_ontology_graph_requires_collection_metadata(TestModel):
    collection = PydontologyCollection()
    collection.register(
        name="people",
        ontology=TestModel,
        description="Person and organization ontology",
    )

    with pytest.raises(
        ValueError, match="Collection metadata is required to build ontology graph"
    ):
        collection.ontology_graph()


def test_collection_ontology_graph_requires_subontology_metadata():
    class Note(Entity):
        """Note entity."""

        note_text: str

    note_ontology = Pydontology(Note)

    collection = PydontologyCollection(
        metadata=BaseMetaData(id="CollectionOntology")
    )
    collection.register(
        name="notes",
        ontology=note_ontology,
        description="Note ontology",
    )

    with pytest.raises(
        ValueError, match="Sub-ontology 'notes' metadata is required for imports"
    ):
        collection.ontology_graph()


def test_collection_ontology_graph_duplicate_ids():
    class Alpha(Entity):
        """Alpha entity."""

        shared: str

    class Beta(Entity):
        """Beta entity."""

        shared: str

    alpha_ontology = Pydontology(
        Alpha,
        BaseMetaData(id="AlphaOntology", comment="Alpha ontology"),
    )
    beta_ontology = Pydontology(
        Beta,
        BaseMetaData(id="BetaOntology", comment="Beta ontology"),
    )

    collection = PydontologyCollection(
        metadata=BaseMetaData(id="CollectionOntology")
    )
    collection.register(
        name="alpha",
        ontology=alpha_ontology,
        description="Alpha ontology",
    )
    collection.register(
        name="beta",
        ontology=beta_ontology,
        description="Beta ontology",
    )

    with pytest.raises(
        ValueError, match="Duplicate @id values found in ontology graph"
    ):
        collection.ontology_graph()
