import pytest

from pydontology.collection import PydontologyCollection
from pydontology.models import JSONLDGraph


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
