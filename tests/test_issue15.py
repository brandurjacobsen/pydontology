"""
Tests for Issue #15: Track attributes by alias

Verifies that the ontology graph uses Pydantic field aliases as property
identifiers where defined, and field names otherwise.
"""

import json
import warnings

import pytest
from pydantic import Field
from rdflib import Graph, Namespace, URIRef

from pydontology.pydontology import Entity, make_model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VOCAB = "http://example.org/vocab#"
VOCAB_NS = Namespace(VOCAB)


def _build_onto_rdf(model_cls) -> Graph:
    """Return an rdflib Graph for the ontology of *model_cls*."""
    Model = make_model(model_cls, name="TestModel")
    onto = Model.ontology_graph()
    g = Graph()
    g.parse(data=onto.model_dump_json(by_alias=True), format="json-ld")
    return g


def _property_ids_in_graph(g: Graph) -> set:
    """Return the local names of all owl:DatatypeProperty / owl:ObjectProperty subjects."""
    ids = set()
    for s in g.subjects():
        uri = str(s)
        if VOCAB in uri:
            ids.add(uri.split(VOCAB)[-1])
    return ids


# ---------------------------------------------------------------------------
# 1. Aliased Attribute Tracking
# ---------------------------------------------------------------------------

class TestAliasedAttributeTracking:
    """The ontology graph must use the alias as the property identifier."""

    def test_alias_used_as_property_identifier(self):
        class AliasedModel(Entity):
            """Model with an aliased field"""
            full_name: str = Field(alias="fullName", description="Full name of the entity")

        g = _build_onto_rdf(AliasedModel)
        prop_ids = _property_ids_in_graph(g)

        assert "fullName" in prop_ids, (
            "Expected alias 'fullName' to appear as a property identifier in the ontology graph"
        )

    def test_original_field_name_not_used_when_alias_present(self):
        class AliasedModel(Entity):
            """Model with an aliased field"""
            full_name: str = Field(alias="fullName", description="Full name of the entity")

        g = _build_onto_rdf(AliasedModel)
        prop_ids = _property_ids_in_graph(g)

        assert "full_name" not in prop_ids, (
            "Original field name 'full_name' should NOT appear as a property identifier "
            "when an alias is defined"
        )


# ---------------------------------------------------------------------------
# 2. Non-Aliased Attribute Tracking
# ---------------------------------------------------------------------------

class TestNonAliasedAttributeTracking:
    """When no alias is set the field name itself must be used."""

    def test_field_name_used_as_property_identifier(self):
        class PlainModel(Entity):
            """Model without aliases"""
            birth_year: int = Field(description="Year of birth")

        g = _build_onto_rdf(PlainModel)
        prop_ids = _property_ids_in_graph(g)

        assert "birth_year" in prop_ids, (
            "Expected field name 'birth_year' to appear as a property identifier "
            "when no alias is defined"
        )


# ---------------------------------------------------------------------------
# 3. Duplicate Alias Detection
# ---------------------------------------------------------------------------

class TestDuplicateAliasDetection:
    """A warning must be emitted when two fields resolve to the same identifier."""

    def test_warning_on_duplicate_alias_in_same_class(self):
        class DuplicateAliasModel(Entity):
            """Model where two fields share the same alias"""
            field_a: str = Field(alias="sharedAlias", description="First field")
            field_b: str = Field(alias="sharedAlias", description="Second field with same alias")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _build_onto_rdf(DuplicateAliasModel)

        messages = [str(w.message) for w in caught]
        assert any("sharedAlias" in m for m in messages), (
            "Expected a warning mentioning 'sharedAlias' when two fields share the same alias"
        )

    def test_warning_on_duplicate_alias_in_inheritance_chain(self):
        class ParentModel(Entity):
            """Parent with a field"""
            label: str = Field(alias="commonAlias", description="Parent field")

        class ChildModel(ParentModel):
            """Child that redefines the same alias"""
            other: str = Field(alias="commonAlias", description="Child field with same alias")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _build_onto_rdf(ChildModel)

        messages = [str(w.message) for w in caught]
        assert any("commonAlias" in m for m in messages), (
            "Expected a warning mentioning 'commonAlias' for duplicate alias in inheritance chain"
        )

    def test_duplicate_alias_later_definition_ignored(self):
        """Only the first definition should appear (no duplicate triples)."""
        class DuplicateAliasModel(Entity):
            """Model where two fields share the same alias"""
            field_a: str = Field(alias="sharedAlias", description="First field")
            field_b: str = Field(alias="sharedAlias", description="Second field with same alias")

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            g = _build_onto_rdf(DuplicateAliasModel)

        prop_uri = URIRef(VOCAB + "sharedAlias")
        triples_for_prop = list(g.triples((prop_uri, None, None)))
        # The property should appear exactly once (not duplicated)
        assert len(triples_for_prop) > 0, "Property 'sharedAlias' should be present in the graph"
        # Verify no duplicate triples exist
        assert len(triples_for_prop) == len(set(triples_for_prop)), (
            "Duplicate triples found for 'sharedAlias' — later definition was not ignored"
        )


# ---------------------------------------------------------------------------
# 4. Serialization Consistency
# ---------------------------------------------------------------------------

class TestSerializationConsistency:
    """Serialized instance keys must match the property identifiers in the ontology graph."""

    def test_serialized_keys_match_ontology_property_identifiers(self):
        class MixedModel(Entity):
            """Model with both aliased and non-aliased fields"""
            full_name: str = Field(alias="fullName", description="Full name")
            age: int = Field(description="Age in years")

        Model = make_model(MixedModel, name="TestModel")
        onto = Model.ontology_graph()
        g = Graph()
        g.parse(data=onto.model_dump_json(by_alias=True), format="json-ld")
        prop_ids = _property_ids_in_graph(g)

        instance = MixedModel(id="http://example.org/person/1", fullName="Alice", age=30)
        serialized = json.loads(instance.model_dump_json(by_alias=True))

        # Collect the field-level keys from the serialized instance
        # (exclude JSON-LD reserved keys starting with '@')
        instance_keys = {k for k in serialized.keys() if not k.startswith("@")}

        for key in instance_keys:
            assert key in prop_ids, (
                f"Serialized key '{key}' not found as a property identifier in the ontology graph"
            )

    def test_alias_key_in_serialization_matches_ontology(self):
        class AliasedModel(Entity):
            """Model with an aliased field"""
            full_name: str = Field(alias="fullName", description="Full name")

        Model = make_model(AliasedModel, name="TestModel")
        onto = Model.ontology_graph()
        g = Graph()
        g.parse(data=onto.model_dump_json(by_alias=True), format="json-ld")
        prop_ids = _property_ids_in_graph(g)

        instance = AliasedModel(id="http://example.org/person/1", fullName="Bob")
        serialized = json.loads(instance.model_dump_json(by_alias=True))

        assert "fullName" in serialized, "Serialized output should use alias 'fullName' as key"
        assert "fullName" in prop_ids, "Ontology graph should use alias 'fullName' as property id"
        assert "full_name" not in serialized, (
            "Serialized output should NOT contain original field name 'full_name'"
        )


# ---------------------------------------------------------------------------
# 5. RDF Parsing
# ---------------------------------------------------------------------------

class TestRDFParsing:
    """Aliased properties must be correctly accessible via rdflib after parsing."""

    def test_aliased_property_accessible_in_rdf_graph(self):
        class AliasedModel(Entity):
            """Model with an aliased field"""
            full_name: str = Field(alias="fullName", description="Full name")

        g = _build_onto_rdf(AliasedModel)
        prop_uri = URIRef(VOCAB + "fullName")

        triples = list(g.triples((prop_uri, None, None)))
        assert len(triples) > 0, (
            f"Expected triples for aliased property <{prop_uri}> in the RDF graph, found none"
        )

    def test_non_aliased_property_accessible_in_rdf_graph(self):
        class PlainModel(Entity):
            """Model without aliases"""
            birth_year: int = Field(description="Year of birth")

        g = _build_onto_rdf(PlainModel)
        prop_uri = URIRef(VOCAB + "birth_year")

        triples = list(g.triples((prop_uri, None, None)))
        assert len(triples) > 0, (
            f"Expected triples for non-aliased property <{prop_uri}> in the RDF graph, found none"
        )

    def test_aliased_property_has_correct_rdf_type(self):
        class AliasedModel(Entity):
            """Model with an aliased field"""
            full_name: str = Field(alias="fullName", description="Full name")

        g = _build_onto_rdf(AliasedModel)
        prop_uri = URIRef(VOCAB + "fullName")

        from rdflib.namespace import OWL, RDF
        rdf_types = list(g.objects(prop_uri, RDF.type))
        assert len(rdf_types) > 0, (
            f"Aliased property <{prop_uri}> should have an rdf:type in the ontology graph"
        )
        assert OWL.DatatypeProperty in rdf_types or OWL.ObjectProperty in rdf_types, (
            f"Aliased property <{prop_uri}> should be typed as owl:DatatypeProperty or "
            f"owl:ObjectProperty"
        )
