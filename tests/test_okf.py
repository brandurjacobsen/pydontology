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
from pydontology.okf import _local_name, _slugify
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


@pytest.fixture
def okf_context():
    """A BaseContext that resolves local names into full IRIs."""
    return BaseContext(vocab="http://example.com/vocab/", base="http://example.com/vocab/")


# ---------------------------------------------------------------------------
# Bundle structure tests
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Index document tests
# ---------------------------------------------------------------------------


def test_index_document(okf_onto):
    """index.md carries the version, the comment, and grouped concept links."""
    text = okf_onto.okf_bundle().render()["index.md"]

    assert text.startswith('---\nokf_version: "0.2"\n---\n')
    assert "An ontology used for testing" in text
    assert text.index("An ontology used for testing") < text.index("# Classes")
    assert "# Classes" in text
    assert "# Properties" in text

    # The RDF-semantics convention note sits between the prefixes and the lists.
    assert "RDF predicates are global" in text
    assert (
        text.index("# Prefixes")
        < text.index("RDF predicates are global")
        < text.index("# Classes")
    )

    # Class and property entries with links, relative to the index (bundle root)
    assert "[Person](classes/Person.md)" in text
    assert "[Company](classes/Company.md)" in text
    assert "[Employee](classes/Employee.md)" in text
    assert "[knows](properties/knows.md)" in text
    assert "[name](properties/name.md)" in text
    assert "[company](properties/company.md)" in text


# ---------------------------------------------------------------------------
# Class document tests
# ---------------------------------------------------------------------------


def test_class_document(okf_onto):
    """Class documents follow the documented body layout."""
    docs = okf_onto.okf_bundle().render()

    person = docs["classes/Person.md"]
    assert 'type: "Ontology Class"' in person
    assert 'title: "Person"' in person
    assert "A person in the test ontology." in person
    assert "Relative IRI" in person
    assert "Person" in person
    assert "# Associated properties" in person
    assert "* [knows](../properties/knows.md)" in person
    assert "* [name](../properties/name.md)" in person

    employee = docs["classes/Employee.md"]
    # Own-declared properties come first, then inherited ones (id-sorted).
    assert "* [company](../properties/company.md)" in employee
    assert (
        employee.index("company.md")
        < employee.index("knows.md")
        < employee.index("name.md")
    )


def test_class_inheritance_markers(okf_onto):
    """Inherited properties are marked with the declaring ancestor."""
    docs = okf_onto.okf_bundle().render()
    employee = docs["classes/Employee.md"]

    # Inherited from Person
    assert "inherited from" in employee
    assert "Person" in employee


# ---------------------------------------------------------------------------
# Property document tests
# ---------------------------------------------------------------------------


def test_property_document(okf_onto):
    """Property documents carry IRI, type, domain/range, and back-links."""
    docs = okf_onto.okf_bundle().render()

    name = docs["properties/name.md"]
    assert 'type: "Ontology Property"' in name
    assert 'title: "name"' in name
    assert "Relative IRI" in name
    assert "DatatypeProperty" in name
    assert "# Associated with" in name
    assert "../classes/Person.md" in name

    company = docs["properties/company.md"]
    assert "Employer" in company
    assert "Relative IRI" in company
    assert "ObjectProperty" in company
    assert "../classes/Employee.md" in company


# ---------------------------------------------------------------------------
# Determinism and write tests
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Slug and path tests
# ---------------------------------------------------------------------------


def test_slugify():
    """_slugify produces filesystem-safe slugs."""
    assert _slugify("Person") == "Person"
    assert _slugify("has/child") == "has-child"
    assert _slugify("A B") == "A-B"


def test_slugify_raises_on_empty():
    """_slugify raises ValueError when the result is empty."""
    with pytest.raises(ValueError):
        _slugify("!!!")


def test_local_name_http_path():
    """A URL path yields the trailing segment, not the scheme prefix.

    Regression test: the ``:`` fallback must only run when neither ``#``
    nor ``/`` is present.  If it runs unconditionally first, an HTTP IRI
    returns ``//host/vocab/Person`` instead of ``Person``.
    """
    assert _local_name("http://example.com/vocab/Person") == "Person"
    assert _local_name("https://example.com/onto/classes/Employee") == "Employee"


def test_local_name_fragment():
    """A ``#`` fragment takes precedence over both ``/`` and ``:``."""
    assert _local_name("http://example.com/vocab#name") == "name"
    # Both a path and a fragment: the fragment wins
    assert _local_name("http://example.com/vocab/onto#Person") == "Person"


def test_local_name_urn():
    """A URN without ``#`` or ``/`` falls back to the last ``:``."""
    assert _local_name("urn:code:Person") == "Person"
    assert _local_name("urn:uuid:1234") == "1234"


def test_local_name_compact_iri():
    """Compact IRIs like ``owl:Thing`` fall back to the last ``:``."""
    assert _local_name("owl:Thing") == "Thing"
    assert _local_name("rdfs:subClassOf") == "subClassOf"


def test_local_name_bare():
    """A bare name with no separator is returned unchanged."""
    assert _local_name("Person") == "Person"
    assert _local_name("") == ""


# ---------------------------------------------------------------------------
# Integration with TestModel
# ---------------------------------------------------------------------------


def test_testmodel_bundle(TestModel):
    """Integration: the shared TestModel schema produces a full bundle."""
    docs = TestModel.okf_bundle().render()

    assert "index.md" in docs
    assert "classes/Employee.md" in docs
    assert "properties/manager.md" in docs


def test_testmodel_relations(TestModel):
    """subPropertyOf/equivalentProperty/inverseOf/equivalentClass lines render."""
    docs = TestModel.okf_bundle().render()

    # acquaintance property document exists
    assert "properties/acquaintance.md" in docs
    assert "knows" in docs["properties/acquaintance.md"]
    # works-for property document exists
    assert any("works-for" in k or "works_for" in k for k in docs)
    # head property has inverseOf
    if "properties/head.md" in docs:
        assert "head_of" in docs["properties/head.md"] or "head-of" in docs["properties/head.md"]


def test_nearest_ancestor_attribution(TestModel):
    """Inherited properties are attributed to the nearest declaring ancestor."""
    manager = TestModel.okf_bundle().render()["classes/Manager.md"]

    # Manager inherits department from Employee (nearest ancestor)
    assert "department" in manager
    assert "Employee" in manager


# ---------------------------------------------------------------------------
# Closed shape tests
# ---------------------------------------------------------------------------


def test_closed_shape_note():
    """A closed class marks its property list as exhaustive."""
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

    assert "Closed shape (`sh:closed`)" in thing
    assert "only these properties are allowed" in thing
    assert "* [name](../properties/name.md)" in thing


# ---------------------------------------------------------------------------
# Prefix and compact IRI tests (with vocab)
# ---------------------------------------------------------------------------


def test_fixed_prefixes_in_index(okf_onto):
    """index.md carries PREFIX blocks for the fixed namespaces."""
    index = okf_onto.okf_bundle().render()["index.md"]

    assert "# Prefixes" in index
    assert "PREFIX owl: <http://www.w3.org/2002/07/owl#>" in index
    assert "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>" in index
    assert "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>" in index
    assert "PREFIX sh: <http://www.w3.org/ns/shacl#>" in index


def test_compact_iri_with_vocab(okf_onto, okf_context):
    """With a vocab, IRIs expand and compact through known prefixes."""
    docs = okf_onto.okf_bundle(context=okf_context).render()

    person = docs["classes/Person.md"]
    # owl:Thing should compact through the owl: prefix
    assert "Thing" in person


def test_relative_iri_without_vocab(okf_onto):
    """Without a vocab, bare names are labelled Relative IRI."""
    docs = okf_onto.okf_bundle().render()
    assert "Relative IRI" in docs["classes/Person.md"]


# ---------------------------------------------------------------------------
# Template override tests
# ---------------------------------------------------------------------------


def test_template_dir_override(okf_onto, tmp_path):
    """Custom templates from a directory override the built-in templates."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    (template_dir / "class.md.j2").write_text(
        "CUSTOM: {{ view.uriref }}\n"
    )
    (template_dir / "property.md.j2").write_text(
        "CUSTOM: {{ view.uriref }}\n"
    )
    (template_dir / "index.md.j2").write_text(
        "INDEX: {{ view.comment or '' }}\n"
    )

    bundle = okf_onto.okf_bundle(template_dir=str(template_dir))
    docs = bundle.render()

    assert "CUSTOM:" in docs["classes/Person.md"]
    assert "Person" in docs["classes/Person.md"]
    assert "INDEX: An ontology used for testing" in docs["index.md"]


# ---------------------------------------------------------------------------
# Missing dependency tests
# ---------------------------------------------------------------------------


def test_missing_jinja2_raises(monkeypatch, okf_onto):
    """A clear ImportError is raised when jinja2 is not installed."""
    import pydontology.okf as okf_module

    monkeypatch.setattr(okf_module, "jinja2", None)
    with pytest.raises(ImportError, match="jinja2"):
        okf_onto.okf_bundle()