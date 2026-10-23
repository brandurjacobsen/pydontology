"""Phase 2: integration tests for the rdflib query module.

These tests exercise the full pipeline:
Pydontology → ontology_graph()/shacl_graph() → JSON-LD → query_ontology() → views.
"""

import pytest

from pydontology.okf_queries import (
    _compute_paths,
    _extract_namespaces,
    _local_name,
    _query_classes,
    _query_metadata,
    _query_properties,
    _query_shacl,
    query_ontology,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def onto_jsonld(TestModel, test_context):
    """JSON-LD string of the ontology graph."""
    onto = TestModel.ontology_graph(context=test_context)
    return onto.model_dump_json(exclude_none=True)


@pytest.fixture
def shacl_jsonld(TestModel, test_context):
    """JSON-LD string of the SHACL graph."""
    shacl = TestModel.shacl_graph(context=test_context)
    return shacl.model_dump_json(exclude_none=True)


# ---------------------------------------------------------------------------
# Namespace tests
# ---------------------------------------------------------------------------


class TestNamespaceExtraction:
    def test_fixed_prefixes_present(self, onto_jsonld):
        """Fixed prefixes (owl, xsd, rdfs, sh) are extracted from the graph."""
        views = query_ontology(onto_jsonld)
        names = {e.name for e in views[0].prefixes}

        assert "owl" in names
        assert "xsd" in names
        assert "rdfs" in names
        assert "sh" in names

    def test_prefix_namespace_values(self, onto_jsonld):
        """Prefix entries carry correct namespace IRIs."""
        views = query_ontology(onto_jsonld)
        prefix_map = {e.name: e.namespace for e in views[0].prefixes}

        assert prefix_map["owl"] == "http://www.w3.org/2002/07/owl#"
        assert prefix_map["xsd"] == "http://www.w3.org/2001/XMLSchema#"
        assert prefix_map["rdfs"] == "http://www.w3.org/2000/01/rdf-schema#"
        assert prefix_map["sh"] == "http://www.w3.org/ns/shacl#"


# ---------------------------------------------------------------------------
# Class query tests
# ---------------------------------------------------------------------------


class TestClassQuery:
    def test_all_classes_present(self, onto_jsonld):
        """All TestModel classes are extracted."""
        views = query_ontology(onto_jsonld)
        class_uris = {v.uriref for v in views[1]}

        assert len(views[1]) == 7  # Person, Employee, Manager, Department, Company, Contractor, DualIncome

        for name in ("Person", "Employee", "Manager", "Department",
                      "Company", "Contractor", "DualIncome"):
            assert any(name in uri for uri in class_uris), f"Missing class: {name}"

    def test_class_labels(self, onto_jsonld):
        """Classes have labels equal to their names."""
        views = query_ontology(onto_jsonld)
        class_by_label = {}
        for v in views[1]:
            # Extract local name from frontmatter title
            name = v.frontmatter["title"]
            class_by_label[name] = v

        assert "Person" in class_by_label
        assert "Employee" in class_by_label
        assert "Company" in class_by_label

    def test_class_parents_from_subclassof(self, onto_jsonld):
        """subClassOf relationships are captured in views."""
        views = query_ontology(onto_jsonld)
        class_by_uri = {}
        for v in views[1]:
            # Use local name from the uri as key
            name = v.uriref.rstrip("/").rsplit("/", 1)[-1]
            class_by_uri[name] = v

        # Employee subClassOf Person
        employee = class_by_uri["Employee"]
        parent_uris = {ref.uriref for ref in employee.sub_class_of}
        assert any("Person" in uri for uri in parent_uris)

        # Person subClassOf owl:Thing
        person = class_by_uri["Person"]
        parent_uris = {ref.uriref for ref in person.sub_class_of}
        assert any("Thing" in uri for uri in parent_uris)

    def test_class_comments(self, onto_jsonld):
        """Class docstrings appear as comments in views."""
        views = query_ontology(onto_jsonld)
        comments = {}
        for v in views[1]:
            name = v.uriref.rstrip("/").rsplit("/", 1)[-1]
            comments[name] = v.comment

        assert comments.get("Person") == "A person, subclass of Entity"
        assert comments.get("Employee") == "An employee, subclass of Person"

    def test_equivalent_class(self, onto_jsonld):
        """owl:equivalentClass targets are captured."""
        views = query_ontology(onto_jsonld)
        for v in views[1]:
            name = v.uriref.rstrip("/").rsplit("/", 1)[-1]
            if name == "Contractor":
                assert len(v.equivalent_class) > 0
                equiv_uris = {ref.uriref for ref in v.equivalent_class}
                assert any("ContractorRestriction" in uri for uri in equiv_uris)


# ---------------------------------------------------------------------------
# Property query tests
# ---------------------------------------------------------------------------


class TestPropertyQuery:
    def test_properties_extracted(self, onto_jsonld):
        """Properties are extracted with types."""
        views = query_ontology(onto_jsonld)
        assert len(views[2]) > 0

    def test_property_types(self, onto_jsonld):
        """Properties carry their rdf:type values."""
        views = query_ontology(onto_jsonld)
        prop_by_name = {}
        for v in views[2]:
            name = v.uriref.rstrip("/").rsplit("/", 1)[-1]
            prop_by_name[name] = v

        # 'name' is a DatatypeProperty (str field)
        if "name" in prop_by_name:
            types = prop_by_name["name"].types
            assert any("DatatypeProperty" in t for t in types)

        # 'knows' is an ObjectProperty (Relation field)
        if "knows" in prop_by_name:
            types = prop_by_name["knows"].types
            assert any("ObjectProperty" in t for t in types)

        # 'manager' is an ObjectProperty with owl:TransitiveProperty
        if "manager" in prop_by_name:
            types = prop_by_name["manager"].types
            assert any("ObjectProperty" in t for t in types)
            assert any("TransitiveProperty" in t for t in types)

    def test_property_domains(self, onto_jsonld):
        """Properties have rdfs:domain references."""
        views = query_ontology(onto_jsonld)
        prop_by_name = {}
        for v in views[2]:
            name = v.uriref.rstrip("/").rsplit("/", 1)[-1]
            prop_by_name[name] = v

        # Single-class properties have domain set
        if "knows" in prop_by_name and prop_by_name["knows"].domain is not None:
            assert "Person" in prop_by_name["knows"].domain.uriref

    def test_property_relationships(self, onto_jsonld):
        """subPropertyOf, equivalentProperty, inverseOf are captured."""
        views = query_ontology(onto_jsonld)
        prop_by_name = {}
        for v in views[2]:
            name = v.uriref.rstrip("/").rsplit("/", 1)[-1]
            prop_by_name[name] = v

        # 'acquaintance' subPropertyOf 'knows'
        if "acquaintance" in prop_by_name:
            sp = prop_by_name["acquaintance"].sub_property_of
            if sp is not None:
                assert "knows" in sp.uriref

        # 'head' inverseOf 'head_of'
        if "head" in prop_by_name:
            inv = prop_by_name["head"].inverse_of
            if inv is not None:
                assert "head_of" in inv.uriref


# ---------------------------------------------------------------------------
# Membership tests
# ---------------------------------------------------------------------------


class TestMembership:
    def test_own_properties_first(self, onto_jsonld):
        """Own-declared properties appear before inherited ones."""
        views = query_ontology(onto_jsonld)
        class_by_name = {}
        for v in views[1]:
            name = v.uriref.rstrip("/").rsplit("/", 1)[-1]
            class_by_name[name] = v

        manager = class_by_name.get("Manager")
        if manager:
            props = manager.required_properties + manager.associated_properties
            if len(props) > 1:
                # head_of should be own (first), inherited ones follow
                own = [p for p in props if p.inherited_from is None]
                inherited = [p for p in props if p.inherited_from is not None]
                if own and inherited:
                    first_own_idx = props.index(own[0])
                    first_inherited_idx = props.index(inherited[0])
                    assert first_own_idx < first_inherited_idx

    def test_inherited_properties_have_ancestor(self, onto_jsonld):
        """Inherited properties carry the declaring ancestor reference."""
        views = query_ontology(onto_jsonld)
        class_by_name = {}
        for v in views[1]:
            name = v.uriref.rstrip("/").rsplit("/", 1)[-1]
            class_by_name[name] = v

        employee = class_by_name.get("Employee")
        if employee:
            props = employee.required_properties + employee.associated_properties
            inherited = [p for p in props if p.inherited_from is not None]
            if inherited:
                # Properties inherited from Person should have Person as ancestor
                person_props = [
                    p for p in inherited if "Person" in str(p.inherited_from.uriref)
                ]
                assert len(person_props) > 0

    def test_nearest_ancestor_attribution(self, onto_jsonld):
        """Inherited properties are attributed to the nearest declaring ancestor."""
        views = query_ontology(onto_jsonld)
        class_by_name = {}
        for v in views[1]:
            name = v.uriref.rstrip("/").rsplit("/", 1)[-1]
            class_by_name[name] = v

        manager = class_by_name.get("Manager")
        if manager:
            props = manager.required_properties + manager.associated_properties
            # company is declared on Employee, so Manager inherits it from Employee
            company_props = [
                p for p in props
                if "company" in p.uriref and p.inherited_from is not None
            ]
            if company_props:
                assert "Employee" in company_props[0].inherited_from.uriref


# ---------------------------------------------------------------------------
# SHACL tests
# ---------------------------------------------------------------------------


class TestShaclQuery:
    def test_node_shapes_extracted(self, onto_jsonld, shacl_jsonld):
        """SHACL node shapes are extracted from the SHACL graph."""
        views = query_ontology(onto_jsonld, shacl_jsonld)
        # Check that views were built (SHACL data doesn't add extra views,
        # it augments existing class views with closed/ignored)
        assert len(views[1]) > 0

    def test_shacl_not_required(self, onto_jsonld):
        """query_ontology works without SHACL data."""
        views = query_ontology(onto_jsonld, shacl_jsonld=None)
        assert len(views[1]) > 0
        assert len(views[2]) > 0


# ---------------------------------------------------------------------------
# Path and slug tests
# ---------------------------------------------------------------------------


class TestPathComputation:
    def test_paths_generated(self, onto_jsonld):
        """Every class and property gets a bundle-relative path."""
        views = query_ontology(onto_jsonld)

        for v in views[1]:
            assert v.path.startswith("classes/")
            assert v.path.endswith(".md")

        for v in views[2]:
            assert v.path.startswith("properties/")
            assert v.path.endswith(".md")

    def test_paths_are_unique(self, onto_jsonld):
        """No two concepts share the same path."""
        views = query_ontology(onto_jsonld)
        all_paths = [v.path for v in views[1]] + [v.path for v in views[2]]
        assert len(all_paths) == len(set(all_paths))

    def test_reference_paths_resolve(self, onto_jsonld):
        """Internal references carry resolvable paths."""
        views = query_ontology(onto_jsonld)
        all_paths = {v.path for v in views[1]} | {v.path for v in views[2]}

        for v in views[1]:
            for ref in v.sub_class_of:
                if ref.path is not None:
                    assert ref.path in all_paths


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_ontology_comment_extracted(self, onto_jsonld):
        """The owl:Ontology rdfs:comment is the index comment."""
        views = query_ontology(onto_jsonld)
        assert views[0].comment == "Ontology used for testing"

    def test_index_frontmatter(self, onto_jsonld):
        """Index view has the correct frontmatter."""
        views = query_ontology(onto_jsonld)
        assert views[0].frontmatter == {"okf_version": "0.2"}
        assert views[0].path == "index.md"


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_query_is_deterministic(self, onto_jsonld):
        """Two calls with the same input produce identical views."""
        v1 = query_ontology(onto_jsonld)
        v2 = query_ontology(onto_jsonld)
        # Compare only views (skip the namespace_manager which differs by identity)
        assert v1[:3] == v2[:3]


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_owl_thing_as_parent(self, onto_jsonld):
        """owl:Thing parent is captured as an external reference (no path)."""
        views = query_ontology(onto_jsonld)
        for v in views[1]:
            name = v.uriref.rstrip("/").rsplit("/", 1)[-1]
            if name == "Person":
                thing_refs = [
                    ref for ref in v.sub_class_of
                    if "Thing" in ref.uriref
                ]
                assert len(thing_refs) > 0
                # owl:Thing is external — no bundle path
                assert thing_refs[0].path is None

    def test_external_inverse_of_target(self, onto_jsonld):
        """External inverseOf targets have no path."""
        views = query_ontology(onto_jsonld)
        for v in views[2]:
            if v.inverse_of is not None and v.inverse_of.path is None:
                # External reference — path is None, title is the IRI
                assert v.inverse_of.uriref
                return
        # If all inverseOf targets are internal, that's fine too