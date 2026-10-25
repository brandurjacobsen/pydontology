"""Phase 1: unit tests for the OKF Jinja2 templates.

These tests render each template against mock view dataclasses and verify
the output shape — section ordering, markdown link format, conditional
sections. They use simple string-based filters that mirror the real filters
which will be wired in Phase 3.
"""

from dataclasses import dataclass, field

import pytest


# ---------------------------------------------------------------------------
# View dataclasses (match the plan shapes, using str in place of URIRef for
# testability — real URIRefs arrive in Phase 3)
# ---------------------------------------------------------------------------


@dataclass
class PrefixEntry:
    name: str
    namespace: str


@dataclass
class Reference:
    uriref: str  # str instead of rdflib.URIRef for tests
    title: str
    path: str | None = None
    comment: str | None = None


@dataclass
class PropertyRef:
    uriref: str
    title: str
    path: str
    inherited_from: Reference | None = None


@dataclass
class ClassView:
    path: str
    frontmatter: dict[str, str]
    comment: str | None
    uriref: str
    sub_class_of: list[Reference] = field(default_factory=list)
    equivalent_class: list[Reference] = field(default_factory=list)
    required_properties: list[PropertyRef] = field(default_factory=list)
    associated_properties: list[PropertyRef] = field(default_factory=list)
    closed: bool = False
    ignored_properties: list[str] = field(default_factory=list)


@dataclass
class PropertyView:
    path: str
    frontmatter: dict[str, str]
    comment: str | None
    uriref: str
    types: list[str] = field(default_factory=list)
    domain: Reference | None = None
    range: Reference | None = None
    sub_property_of: Reference | None = None
    equivalent_property: Reference | None = None
    inverse_of: Reference | None = None
    required_by: list[Reference] = field(default_factory=list)
    associated_with: list[Reference] = field(default_factory=list)


@dataclass
class IndexView:
    path: str
    frontmatter: dict[str, str]
    comment: str | None
    prefixes: list[PrefixEntry] = field(default_factory=list)
    classes: list[Reference] = field(default_factory=list)
    properties: list[Reference] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Jinja2 filter implementations (simple stubs for template testing)
# ---------------------------------------------------------------------------


def _compact_iri(value: str) -> str:
    """Stub: return the value as-is. Real filter uses namespace_manager.qname."""
    return value


def _iri_label(value: str) -> str:
    """Stub: return 'IRI' for absolute/compact, 'Relative IRI' for bare names."""
    if ":" in value or value.startswith("http"):
        return "IRI"
    return "Relative IRI"


def _make_ref(source_path: str):
    """Stub ref filter: links relative to the source document's directory."""
    from os.path import dirname, relpath

    def _ref(value) -> str:
        if value.path:
            return f"[{value.title}]({relpath(value.path, dirname(source_path) or '.')})"
        return value.title

    return _ref


# ---------------------------------------------------------------------------
# Jinja2 environment fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def env():
    import jinja2

    loader = jinja2.PackageLoader("pydontology", "templates")
    e = jinja2.Environment(loader=loader, autoescape=False)
    e.filters["compact_iri"] = _compact_iri
    e.filters["iri_label"] = _iri_label
    return e


# ---------------------------------------------------------------------------
# Template rendering helpers
# ---------------------------------------------------------------------------


def render(env, template_name: str, view) -> str:
    """Render a template and return the stripped body.

    Binds the ``ref`` filter per-view so links mirror the real, per-document
    relative-path behaviour.
    """
    env.filters["ref"] = _make_ref(view.path)
    template = env.get_template(template_name)
    return template.render(view=view).strip()


# ---------------------------------------------------------------------------
# Class template tests
# ---------------------------------------------------------------------------


class TestClassTemplate:
    """class.md.j2 rendering tests."""

    def test_full_class_with_comment_and_inheritance(self, env):
        view = ClassView(
            path="classes/Employee.md",
            frontmatter={
                "type": "Ontology Class",
                "title": "Employee",
                "resource": "Employee",
            },
            comment="An employee, a kind of person.",
            uriref="Employee",
            sub_class_of=[
                Reference(uriref="Person", title="Person", path="classes/Person.md")
            ],
            associated_properties=[
                PropertyRef(
                    uriref="company",
                    title="company",
                    path="properties/company.md",
                ),
                PropertyRef(
                    uriref="knows",
                    title="knows",
                    path="properties/knows.md",
                    inherited_from=Reference(
                        uriref="Person",
                        title="Person",
                        path="classes/Person.md",
                    ),
                ),
            ],
        )

        body = render(env, "class.md.j2", view)

        # Comment appears as leading paragraph
        assert body.startswith("An employee, a kind of person.")
        # IRI label and value
        assert "Relative IRI: Employee" in body
        # Subclass link (relative to classes/, so sibling = bare name)
        assert "Subclass of: [Person](Person.md)" in body
        # Section heading
        assert "# Associated properties" in body
        # Own property (no inheritance marker)
        assert "* [company](../properties/company.md)" in body
        # Inherited property
        assert (
            "* [knows](../properties/knows.md) - inherited from "
            "[Person](Person.md)" in body
        )
        # Own before inherited
        assert body.index("company.md") < body.index("knows.md")

    def test_class_direct_entity_subclass(self, env):
        """A class inheriting directly from Entity gets owl:Thing as parent."""
        view = ClassView(
            path="classes/Person.md",
            frontmatter={
                "type": "Ontology Class",
                "title": "Person",
                "resource": "Person",
            },
            comment="A person in the test ontology.",
            uriref="Person",
            sub_class_of=[
                Reference(uriref="owl:Thing", title="owl:Thing", path=None)
            ],
            associated_properties=[
                PropertyRef(
                    uriref="name", title="name", path="properties/name.md"
                ),
            ],
        )

        body = render(env, "class.md.j2", view)

        assert "A person in the test ontology." in body
        assert "Relative IRI: Person" in body
        # owl:Thing has no path, so rendered as bare title (no link)
        assert "Subclass of: owl:Thing" in body
        assert "# Associated properties" in body
        assert "* [name](../properties/name.md)" in body

    def test_no_comment(self, env):
        """Class without a comment omits the leading paragraph."""
        view = ClassView(
            path="classes/X.md",
            frontmatter={"type": "Ontology Class", "title": "X", "resource": "X"},
            comment=None,
            uriref="X",
        )

        body = render(env, "class.md.j2", view)

        # Body should start with the IRI line, not a blank line
        assert body.startswith("Relative IRI: X")

    def test_closed_shape(self, env):
        """Closed shape emits a note and lists ignored properties."""
        view = ClassView(
            path="classes/ClosedThing.md",
            frontmatter={
                "type": "Ontology Class",
                "title": "ClosedThing",
                "resource": "ClosedThing",
            },
            comment="A closed thing.",
            uriref="ClosedThing",
            closed=True,
            ignored_properties=["rdf:type"],
            associated_properties=[
                PropertyRef(
                    uriref="name", title="name", path="properties/name.md"
                ),
            ],
        )

        body = render(env, "class.md.j2", view)

        assert (
            "Closed shape (`sh:closed`): only these properties are allowed "
            "(plus ignored: rdf:type)." in body
        )
        assert "* [name](../properties/name.md)" in body

    def test_closed_shape_no_ignored(self, env):
        """Closed shape without ignored properties."""
        view = ClassView(
            path="classes/X.md",
            frontmatter={"type": "Ontology Class", "title": "X", "resource": "X"},
            comment=None,
            uriref="X",
            closed=True,
        )

        body = render(env, "class.md.j2", view)

        assert "Closed shape (`sh:closed`): only these properties are allowed." in body
        # No trailing parenthetical about ignored
        assert "(plus ignored:" not in body

    def test_equivalent_class(self, env):
        """Equivalent class entries render."""
        view = ClassView(
            path="classes/Contractor.md",
            frontmatter={
                "type": "Ontology Class",
                "title": "Contractor",
                "resource": "Contractor",
            },
            comment=None,
            uriref="Contractor",
            equivalent_class=[
                Reference(
                    uriref="ContractorRestriction",
                    title="ContractorRestriction",
                    path=None,
                ),
            ],
        )

        body = render(env, "class.md.j2", view)

        assert "Equivalent to: ContractorRestriction" in body

    def test_empty_properties(self, env):
        """Class with no properties omits property sections entirely."""
        view = ClassView(
            path="classes/X.md",
            frontmatter={"type": "Ontology Class", "title": "X", "resource": "X"},
            comment=None,
            uriref="X",
        )

        body = render(env, "class.md.j2", view)
        assert "# Required properties" not in body
        assert "# Associated properties" not in body

    def test_compact_iri(self, env):
        """With a vocab, compact IRIs are used."""
        view = ClassView(
            path="classes/Person.md",
            frontmatter={
                "type": "Ontology Class",
                "title": "Person",
                "resource": "ex:Person",
            },
            comment=None,
            uriref="ex:Person",
            sub_class_of=[
                Reference(uriref="owl:Thing", title="owl:Thing", path=None)
            ],
        )

        body = render(env, "class.md.j2", view)

        assert "IRI: ex:Person" in body
        assert "Relative IRI" not in body


# ---------------------------------------------------------------------------
# Property template tests
# ---------------------------------------------------------------------------


class TestPropertyTemplate:
    """property.md.j2 rendering tests."""

    def test_property_with_domain_and_range(self, env):
        view = PropertyView(
            path="properties/company.md",
            frontmatter={
                "type": "Ontology Property",
                "title": "company",
                "resource": "company",
            },
            comment="Employer",
            uriref="company",
            types=["owl:ObjectProperty"],
            domain=Reference(
                uriref="Employee",
                title="Employee",
                path="classes/Employee.md",
            ),
            range=Reference(
                uriref="Company",
                title="Company",
                path="classes/Company.md",
            ),
            associated_with=[
                Reference(
                    uriref="Employee",
                    title="Employee",
                    path="classes/Employee.md",
                ),
            ],
        )

        body = render(env, "property.md.j2", view)

        assert body.startswith("Employer")
        assert "Relative IRI: company" in body
        assert "Type: owl:ObjectProperty" in body
        assert "RDFS domain: [Employee](../classes/Employee.md)" in body
        assert "RDFS range: [Company](../classes/Company.md)" in body
        assert "# Associated with" in body
        assert "* [Employee](../classes/Employee.md)" in body

    def test_multi_class_property_no_domain_range(self, env):
        """Property defined in multiple classes suppresses domain/range."""
        view = PropertyView(
            path="properties/name.md",
            frontmatter={
                "type": "Ontology Property",
                "title": "name",
                "resource": "name",
            },
            comment=None,
            uriref="name",
            types=["owl:DatatypeProperty", "xsd:string"],
            associated_with=[
                Reference(uriref="Person", title="Person", path="classes/Person.md"),
                Reference(uriref="Company", title="Company", path="classes/Company.md"),
            ],
        )

        body = render(env, "property.md.j2", view)

        assert "Relative IRI: name" in body
        assert "Type: owl:DatatypeProperty, xsd:string" in body
        assert "RDFS domain:" not in body
        assert "RDFS range:" not in body
        assert "# Associated with" in body
        assert "* [Person](../classes/Person.md)" in body
        assert "* [Company](../classes/Company.md)" in body

    def test_property_relations(self, env):
        """subPropertyOf, equivalentProperty, inverseOf all render."""
        view = PropertyView(
            path="properties/acquaintance.md",
            frontmatter={
                "type": "Ontology Property",
                "title": "acquaintance",
                "resource": "acquaintance",
            },
            comment=None,
            uriref="acquaintance",
            types=["owl:ObjectProperty"],
            sub_property_of=Reference(
                uriref="knows",
                title="knows",
                path="properties/knows.md",
            ),
            equivalent_property=Reference(
                uriref="works_at",
                title="works_at",
                path=None,
            ),
            inverse_of=Reference(
                uriref="head_of",
                title="head_of",
                path="properties/head-of.md",
            ),
            associated_with=[
                Reference(uriref="Person", title="Person", path="classes/Person.md"),
            ],
        )

        body = render(env, "property.md.j2", view)

        assert "Subproperty of: [knows](knows.md)" in body
        assert "Equivalent to: works_at" in body
        assert "Inverse of: [head_of](head-of.md)" in body

    def test_no_comment(self, env):
        """Property without comment starts with IRI line."""
        view = PropertyView(
            path="properties/x.md",
            frontmatter={
                "type": "Ontology Property",
                "title": "x",
                "resource": "x",
            },
            comment=None,
            uriref="x",
            types=["owl:DatatypeProperty", "xsd:integer"],
        )

        body = render(env, "property.md.j2", view)
        assert body.startswith("Relative IRI: x")

    def test_empty_defined_in(self, env):
        """Property with no required or associated classes omits both sections."""
        view = PropertyView(
            path="properties/x.md",
            frontmatter={
                "type": "Ontology Property",
                "title": "x",
                "resource": "x",
            },
            comment=None,
            uriref="x",
            required_by=[],
            associated_with=[],
        )

        body = render(env, "property.md.j2", view)
        assert "# Required by" not in body
        assert "# Associated with" not in body

    def test_compact_iri(self, env):
        """With a vocab, compact IRIs are used."""
        view = PropertyView(
            path="properties/name.md",
            frontmatter={
                "type": "Ontology Property",
                "title": "name",
                "resource": "ex:name",
            },
            comment=None,
            uriref="ex:name",
            types=["owl:DatatypeProperty", "xsd:string"],
        )

        body = render(env, "property.md.j2", view)
        assert "IRI: ex:name" in body
        assert "Relative IRI" not in body


# ---------------------------------------------------------------------------
# Index template tests
# ---------------------------------------------------------------------------


class TestIndexTemplate:
    """index.md.j2 rendering tests."""

    def test_full_index(self, env):
        view = IndexView(
            path="index.md",
            frontmatter={"okf_version": "0.2"},
            comment="An ontology used for testing",
            prefixes=[
                PrefixEntry(name="owl", namespace="http://www.w3.org/2002/07/owl#"),
                PrefixEntry(name="xsd", namespace="http://www.w3.org/2001/XMLSchema#"),
                PrefixEntry(
                    name="rdfs", namespace="http://www.w3.org/2000/01/rdf-schema#"
                ),
                PrefixEntry(name="sh", namespace="http://www.w3.org/ns/shacl#"),
            ],
            classes=[
                Reference(
                    uriref="Company",
                    title="Company",
                    path="classes/Company.md",
                    comment="A company. More detail here.",
                ),
                Reference(
                    uriref="Employee",
                    title="Employee",
                    path="classes/Employee.md",
                    comment="An employee, a kind of person.",
                ),
                Reference(
                    uriref="Person",
                    title="Person",
                    path="classes/Person.md",
                    comment="A person in the test ontology.",
                ),
            ],
            properties=[
                Reference(
                    uriref="company",
                    title="company",
                    path="properties/company.md",
                    comment="Employer",
                ),
                Reference(
                    uriref="knows",
                    title="knows",
                    path="properties/knows.md",
                    comment="A friend",
                ),
                Reference(
                    uriref="name",
                    title="name",
                    path="properties/name.md",
                    comment=None,
                ),
            ],
        )

        body = render(env, "index.md.j2", view)

        # Comment before sections
        assert body.index("An ontology used for testing") < body.index("# Prefixes")

        # Prefixes section
        assert "# Prefixes" in body
        assert "PREFIX owl: <http://www.w3.org/2002/07/owl#>" in body
        assert "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>" in body
        assert "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>" in body
        assert "PREFIX sh: <http://www.w3.org/ns/shacl#>" in body

        # Conventions note between prefixes and classes
        assert "RDF predicates are global" in body
        assert (
            body.index("# Prefixes")
            < body.index("RDF predicates are global")
            < body.index("# Classes")
        )

        # Classes section with comments (relative to bundle root)
        assert "# Classes" in body
        assert (
            "* [Company](classes/Company.md) - A company. More detail here." in body
        )
        assert (
            "* [Person](classes/Person.md) - A person in the test ontology." in body
        )

        # Properties section — with and without comments
        assert "# Properties" in body
        assert "* [company](properties/company.md) - Employer" in body
        assert "* [knows](properties/knows.md) - A friend" in body
        # No comment for multi-class property
        assert "* [name](properties/name.md)" in body

    def test_no_comment(self, env):
        """Index without ontology comment starts at # Prefixes."""
        view = IndexView(
            path="index.md",
            frontmatter={"okf_version": "0.2"},
            comment=None,
            prefixes=[],
        )

        body = render(env, "index.md.j2", view)
        assert body.startswith("# Prefixes")

    def test_empty_lists(self, env):
        """Index with no classes or properties still shows headings."""
        view = IndexView(
            path="index.md",
            frontmatter={"okf_version": "0.2"},
            comment=None,
            prefixes=[],
        )

        body = render(env, "index.md.j2", view)
        assert "# Classes" in body
        assert "# Properties" in body

    def test_no_ex_prefix_when_no_vocab(self, env):
        """Without a vocab, no ex: prefix appears."""
        view = IndexView(
            path="index.md",
            frontmatter={"okf_version": "0.2"},
            comment=None,
            prefixes=[
                PrefixEntry(name="owl", namespace="http://www.w3.org/2002/07/owl#"),
            ],
        )

        body = render(env, "index.md.j2", view)
        assert "PREFIX ex:" not in body


# ---------------------------------------------------------------------------
# Cross-template consistency tests
# ---------------------------------------------------------------------------


def test_templates_are_deterministic(env):
    """Rendering the same view twice produces identical output."""
    view = ClassView(
        path="classes/X.md",
        frontmatter={"type": "Ontology Class", "title": "X", "resource": "X"},
        comment=None,
        uriref="X",
        associated_properties=[
            PropertyRef(uriref="a", title="a", path="properties/a.md"),
            PropertyRef(uriref="b", title="b", path="properties/b.md"),
        ],
    )
    assert render(env, "class.md.j2", view) == render(env, "class.md.j2", view)


def test_all_templates_load(env):
    """All three templates are loadable."""
    assert env.get_template("class.md.j2") is not None
    assert env.get_template("property.md.j2") is not None
    assert env.get_template("index.md.j2") is not None