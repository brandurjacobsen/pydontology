from typing import Annotated

import pytest
from pydantic import Field

from pydontology import (
    BaseContext,
    BaseMetaData,
    Entity,
    OKFBundle,
    Pydontology,
    Relation,
)
from pydontology.models import OntologyClass, OntologyProperty
from pydontology.okf import CONVENTIONS_NOTE, build_okf_bundle
from pydontology.rdfs import RDFSAnnotation as RDFS
from pydontology.shacl import SHACLAnnotation as SH


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

    # The RDF-semantics convention note sits between the prefixes and the lists.
    assert CONVENTIONS_NOTE in text
    assert (
        text.index("# Prefixes")
        < text.index(CONVENTIONS_NOTE)
        < text.index("# Classes")
    )

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
    assert "# Applicable properties" in person
    assert "# Properties\n" not in person
    assert "* [name](/properties/name.md)" in person
    assert "* [knows](/properties/knows.md)" in person

    employee = docs["classes/Employee.md"]
    assert "Subclass of: [Person](/classes/Person.md)" in employee
    # Own-declared properties come first, then inherited ones (id-sorted).
    assert "* [company](/properties/company.md)" in employee
    assert (
        "* [knows](/properties/knows.md) - inherited from [Person](/classes/Person.md)"
        in employee
    )
    assert (
        "* [name](/properties/name.md) - inherited from [Person](/classes/Person.md)"
        in employee
    )
    assert (
        employee.index("company.md")
        < employee.index("knows.md")
        < employee.index("name.md")
    )


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
    assert "RDFS domain:" not in name
    assert "RDFS range:" not in name

    company = docs["properties/company.md"]
    assert "Employer" in company
    assert "Relative IRI: company" in company
    assert "Type: owl:ObjectProperty" in company
    assert "RDFS domain: [Employee](/classes/Employee.md)" in company
    assert "RDFS range: [Company](/classes/Company.md)" in company
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
    assert "RDFS domain: [Employee](/classes/Employee.md)" in manager
    assert "RDFS range: [Manager](/classes/Manager.md)" in manager


TEST_VOCAB = "http://example.com/vocab/"


@pytest.fixture
def okf_context():
    """A BaseContext that resolves local names into compact IRIs."""
    return BaseContext(vocab=TEST_VOCAB, base=TEST_VOCAB)


def test_prefix_section_lists_context_namespaces(okf_onto, okf_context):
    """index.md carries a copy-pasteable PREFIX block for the context."""
    index = okf_onto.okf_bundle(context=okf_context).render()["index.md"]

    assert "# Prefixes" in index
    assert f"PREFIX ex: <{TEST_VOCAB}>" in index
    assert "PREFIX owl: <http://www.w3.org/2002/07/owl#>" in index
    assert "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>" in index
    assert "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>" in index
    assert "PREFIX sh: <http://www.w3.org/ns/shacl#>" in index


def test_compact_iri_when_context_supplied(okf_onto, okf_context):
    """With a vocab, ids and resources render as ex: compact IRIs."""
    docs = okf_onto.okf_bundle(context=okf_context).render()

    person = docs["classes/Person.md"]
    assert 'resource: "ex:Person"' in person
    assert "IRI: ex:Person" in person
    assert "Subclass of: owl:Thing" in person
    assert "Relative IRI" not in person

    name = docs["properties/name.md"]
    assert 'resource: "ex:name"' in name
    assert "IRI: ex:name" in name


def test_default_context_falls_back_to_relative_names(okf_onto):
    """Without a vocab, bare names stay relative and only fixed prefixes show."""
    docs = okf_onto.okf_bundle().render()

    index = docs["index.md"]
    assert "PREFIX ex:" not in index
    assert "PREFIX owl:" in index
    assert "Relative IRI: Person" in docs["classes/Person.md"]


def test_unbundled_target_uses_compact_iri(okf_context):
    """An external inverseOf target renders as a compact or verbatim IRI."""
    properties = [
        OntologyProperty(
            id="related_to",
            type=["owl:ObjectProperty"],
            inverseOf=Relation(id="schema:related"),
        )
    ]
    bundle = build_okf_bundle(
        name="Bundle",
        metadata=BaseMetaData(id="Bundle"),
        classes=[],
        properties=properties,
        defined_in={"related_to": []},
        context=okf_context,
    )
    document = bundle.render()["properties/related-to.md"]

    assert "IRI: ex:related_to" in document
    assert "Inverse of: schema:related" in document


def test_relations_render_with_internal_links(TestModel):
    """subPropertyOf/equivalentProperty/inverseOf/equivalentClass lines render."""
    docs = TestModel.okf_bundle().render()

    assert (
        "Subproperty of: [knows](/properties/knows.md)"
        in docs["properties/acquaintance.md"]
    )
    assert "Equivalent to: works_at" in docs["properties/works-for.md"]
    assert "Inverse of: [head_of](/properties/head-of.md)" in docs["properties/head.md"]
    assert "Equivalent to: ContractorRestriction" in docs["classes/Contractor.md"]


def test_applicable_properties_attribute_nearest_ancestor(TestModel):
    """Inherited properties are attributed to the nearest declaring ancestor."""
    manager = TestModel.okf_bundle().render()["classes/Manager.md"]

    # Own-declared property, unmarked.
    assert "* [head_of](/properties/head-of.md)" in manager
    # Declared on Employee (the nearest ancestor), not Person.
    assert (
        "* [company](/properties/company.md) - inherited from "
        "[Employee](/classes/Employee.md)" in manager
    )
    # Declared on Person, the grandparent.
    assert (
        "* [name](/properties/name.md) - inherited from [Person](/classes/Person.md)"
        in manager
    )


def test_closed_shape_note():
    """A closed class marks its property list as exhaustive."""
    from typing import Annotated

    class ClosedThing(Entity):
        """A closed thing."""

        name: str = Field(default="x")

    ontology = Annotated[
        ClosedThing,
        SH.closed(True),
        SH.ignoredProperties(["rdf:type"]),
    ]
    onto = Pydontology(ontology, BaseMetaData(id="ClosedOnto"))
    thing = onto.okf_bundle().render()["classes/ClosedThing.md"]

    assert (
        "Closed shape (`sh:closed`): only these properties are allowed "
        "(plus ignored: rdf:type)." in thing
    )
    assert "* [name](/properties/name.md)" in thing
