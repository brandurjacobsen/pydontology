from typing import Annotated

import pytest
from pydantic import Field

from pydontology import BaseMetaData, Entity, OKFBundle, Pydontology, Relation
from pydontology.models import OntologyClass, OntologyProperty
from pydontology.okf import build_okf_bundle
from pydontology.rdfs import RDFSAnnotation as RDFS


class Person(Entity):
    """A person in the test ontology."""

    name: str = Field(description="Person's name")
    knows: Relation | None = Field(default=None, description="A friend")


class Employee(Person):
    """An employee, a kind of person."""

    company: Annotated[Relation, RDFS.range("Company")] = Field(description="Employer")


class Company(Entity):
    """A company.

    More detail here.
    """

    name: str = Field(description="Company name")


@pytest.fixture
def okf_onto():
    """A Pydontology instance with a label and a comment for the bundle root."""
    metadata = BaseMetaData(
        id="TestOntology",
        label="Test Ontology",
        comment="An ontology used for testing",
    )
    return Pydontology(Person | Employee | Company, metadata)


def test_bundle_type_and_root_name(okf_onto):
    """The bundle is an OKFBundle whose root is the slugified metadata label."""
    bundle = okf_onto.okf_bundle()
    assert isinstance(bundle, OKFBundle)
    assert bundle.name == "Test-Ontology"


def test_root_name_falls_back_to_id():
    """Without a label, the bundle root is the slugified metadata id."""
    onto = Pydontology(Person | Company, BaseMetaData(id="Just Id"))
    assert onto.okf_bundle().name == "Just-Id"


def test_missing_metadata_raises():
    """Requesting a bundle without metadata raises a clear error."""
    onto = Pydontology(Person | Company)
    with pytest.raises(ValueError, match="metadata is required"):
        onto.okf_bundle()


def test_index_document(okf_onto):
    """index.md carries the version, the comment, and grouped concept links."""
    text = okf_onto.okf_bundle().render()["index.md"]

    assert text.startswith('---\nokf_version: "0.2"\n---\n')
    assert text.index("An ontology used for testing") < text.index("# Classes")
    assert "# Classes" in text
    assert "# Properties" in text

    assert "* [Person](/classes/Person.md) - A person in the test ontology." in text
    # A multi-line class docstring is collapsed to one line in the index.
    assert "* [Company](/classes/Company.md) - A company. More detail here." in text
    assert "* [knows](/properties/knows.md) - A friend" in text
    # 'name' is defined in two classes, so its description is suppressed.
    assert "* [name](/properties/name.md)" in text


def test_class_document(okf_onto):
    """Class documents follow the documented body layout."""
    docs = okf_onto.okf_bundle().render()

    person = docs["classes/Person.md"]
    assert person.startswith(
        '---\ntype: "Ontology Class"\ntitle: "Person"\nresource: "Person"\n---\n'
    )
    assert "A person in the test ontology." in person
    assert "Relative IRI: Person" in person
    assert "Subclass of: owl:Thing" in person
    assert "* [name](/properties/name.md)" in person
    assert "* [knows](/properties/knows.md)" in person

    employee = docs["classes/Employee.md"]
    assert "Subclass of: [Person](/classes/Person.md)" in employee
    assert "* [company](/properties/company.md)" in employee
    # Only properties defined directly on the class are listed.
    assert "/properties/name.md" not in employee
    assert "/properties/knows.md" not in employee


def test_property_document(okf_onto):
    """Property documents carry IRI, type, domain/range, and back-links."""
    docs = okf_onto.okf_bundle().render()

    name = docs["properties/name.md"]
    assert name.startswith(
        '---\ntype: "Ontology Property"\ntitle: "name"\nresource: "name"\n---\n'
    )
    assert "Relative IRI: name" in name
    assert "Type: owl:DatatypeProperty, xsd:string" in name
    assert "# Defined in" in name
    assert "* [Person](/classes/Person.md)" in name
    assert "* [Company](/classes/Company.md)" in name
    # 'name' is defined in multiple classes, so domain/range are suppressed.
    assert "Domain:" not in name
    assert "Range:" not in name

    company = docs["properties/company.md"]
    assert "Employer" in company
    assert "Relative IRI: company" in company
    assert "Type: owl:ObjectProperty" in company
    assert "Domain: [Employee](/classes/Employee.md)" in company
    assert "Range: [Company](/classes/Company.md)" in company
    assert "* [Employee](/classes/Employee.md)" in company


def test_render_is_deterministic(okf_onto):
    """Two builds of the same ontology render identically."""
    assert okf_onto.okf_bundle().render() == okf_onto.okf_bundle().render()


def test_write_tree(okf_onto, tmp_path):
    """write() creates the expected tree and leaves unrelated files alone."""
    bundle = okf_onto.okf_bundle()
    root = bundle.write(tmp_path)

    assert root == tmp_path / "Test-Ontology"
    written = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.md"))
    assert written == [
        "classes/Company.md",
        "classes/Employee.md",
        "classes/Person.md",
        "index.md",
        "properties/company.md",
        "properties/knows.md",
        "properties/name.md",
    ]
    assert (root / "index.md").read_text() == bundle.render()["index.md"]

    keep = root / "keep.txt"
    keep.write_text("keep")
    bundle.write(tmp_path)
    assert keep.read_text() == "keep"


def test_unsafe_id_is_slugged():
    """Concept paths use slugified ids."""
    properties = [OntologyProperty(id="has/child", type=["owl:ObjectProperty"])]
    bundle = build_okf_bundle(
        name="Bundle",
        metadata=BaseMetaData(id="Bundle"),
        classes=[],
        properties=properties,
        defined_in={"has/child": []},
    )
    assert "properties/has-child.md" in bundle.render()


def test_absolute_id_uses_iri_label():
    """An absolute-id concept is labelled 'IRI', not 'Relative IRI'."""
    properties = [
        OntologyProperty(id="http://example.com/p", type=["owl:ObjectProperty"])
    ]
    bundle = build_okf_bundle(
        name="Bundle",
        metadata=BaseMetaData(id="Bundle"),
        classes=[],
        properties=properties,
        defined_in={"http://example.com/p": []},
    )
    document = bundle.render()["properties/http-example-com-p.md"]
    assert "IRI: http://example.com/p" in document
    assert "Relative IRI" not in document


def test_slug_collision_raises():
    """Two ids that collapse to one slug raise a clear error."""
    classes = [OntologyClass(id="A B"), OntologyClass(id="A-B")]
    with pytest.raises(ValueError, match="collision"):
        build_okf_bundle(
            name="Bundle",
            metadata=BaseMetaData(id="Bundle"),
            classes=classes,
            properties=[],
            defined_in={},
        )


def test_testmodel_bundle(TestModel):
    """Integration: the shared TestModel schema produces a full bundle."""
    docs = TestModel.okf_bundle().render()

    assert "index.md" in docs
    assert "classes/Employee.md" in docs
    assert "properties/manager.md" in docs
    assert "Subclass of: [Employee](/classes/Employee.md)" in docs["classes/Manager.md"]
    assert "Subclass of: [Person](/classes/Person.md)" in docs["classes/Employee.md"]

    manager = docs["properties/manager.md"]
    assert "Relative IRI: manager" in manager
    assert "Type: owl:ObjectProperty, owl:TransitiveProperty" in manager
    assert "Domain: [Employee](/classes/Employee.md)" in manager
    assert "Range: [Manager](/classes/Manager.md)" in manager
