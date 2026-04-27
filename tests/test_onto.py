import pytest
from rdflib import OWL, RDF, RDFS, Graph, Namespace

from pydontology.pydontology import BaseContext, JSONLDGraph

# See conftest.py for TestModel definition


@pytest.fixture
def onto_graph(TestModel):
    """Fixture providing the generated ontology graph"""
    return TestModel.ontology_graph()


@pytest.fixture
def onto_graph_json(onto_graph):
    """Fixture returing the ontology graph as json-ld"""
    return onto_graph.model_dump_json(exclude_none=True)


@pytest.fixture
def rdf_graph(onto_graph_json):
    """Fixture returing the ontology graph as an rdflib Graph"""
    g = Graph()
    g.parse(data=onto_graph_json, format="json-ld")
    return g


@pytest.fixture
def vocab_namespace():
    """Fixture providing the vocabulary namespace"""
    return Namespace(BaseContext().vocab)


def test_returns_jsonld_graph(onto_graph):
    """Test that onto_graph returns a JSONLDGraph instance"""
    assert isinstance(onto_graph, JSONLDGraph)


def test_rdflib_can_parse_rdf_graph(rdf_graph):
    """Test that rdflib can parse the ontology graph and it contains triples"""
    assert len(rdf_graph) > 0


def test_ontology_classes_present(rdf_graph, vocab_namespace):
    """Test that all expected classes are present in ontology graph"""
    VOCAB = vocab_namespace

    # Verify all classes exist as rdfs:Class
    assert (VOCAB.Person, RDF.type, RDFS.Class) in rdf_graph
    assert (VOCAB.Employee, RDF.type, RDFS.Class) in rdf_graph
    assert (VOCAB.Manager, RDF.type, RDFS.Class) in rdf_graph
    assert (VOCAB.Department, RDF.type, RDFS.Class) in rdf_graph
    assert (VOCAB.Company, RDF.type, RDFS.Class) in rdf_graph

    # Count total classes (should be exactly 6)
    classes = list(rdf_graph.subjects(RDF.type, RDFS.Class))
    assert len(classes) == 6


def test_ontology_inheritance(rdf_graph, vocab_namespace):
    """Test that ontology classes are rdfs subClassOf parent (Entity) class or owl:Thing (default)"""
    VOCAB = vocab_namespace

    # Employee should be subclass of Person
    assert (VOCAB.Employee, RDFS.subClassOf, VOCAB.Person) in rdf_graph

    # Manager should be subclass of Employee
    assert (VOCAB.Manager, RDFS.subClassOf, VOCAB.Employee) in rdf_graph

    # Person should be subclass of owl:Thing (Entity)
    assert (VOCAB.Person, RDFS.subClassOf, OWL.Thing) in rdf_graph

    # Department should be subclass of owl:Thing (Entity)
    assert (VOCAB.Department, RDFS.subClassOf, OWL.Thing) in rdf_graph

    # Company should be subclass of owl:Thing (Entity)
    assert (VOCAB.Company, RDFS.subClassOf, OWL.Thing) in rdf_graph


def test_ontology_properties_present(rdf_graph, vocab_namespace):
    """Test that all expected properties are present"""
    VOCAB = vocab_namespace

    # Get all properties (both ObjectProperty and DatatypeProperty)
    object_props = list(rdf_graph.subjects(RDF.type, OWL.ObjectProperty))
    datatype_props = list(rdf_graph.subjects(RDF.type, OWL.DatatypeProperty))
    all_props = object_props + datatype_props

    # Should have exactly 13 properties
    assert len(all_props) == 13

    # Verify each expected property exists
    assert VOCAB.name in all_props
    assert VOCAB.age in all_props
    assert VOCAB.knows in all_props
    assert VOCAB.employee_id in all_props
    assert VOCAB.manager in all_props
    assert VOCAB.department in all_props
    assert VOCAB.company in all_props
    assert VOCAB.head_of in all_props
    assert VOCAB.vice_head_of in all_props
    assert VOCAB.head in all_props
    assert VOCAB.vice_head in all_props
    assert VOCAB.ceo in all_props


def test_ontology_symmetric_property(rdf_graph, vocab_namespace):
    """Test that symmetric properties are correctly annotated"""
    VOCAB = vocab_namespace

    # Check knows property is symmetric
    assert (VOCAB.knows, RDF.type, OWL.SymmetricProperty) in rdf_graph


def test_ontology_transitive_property(rdf_graph, vocab_namespace):
    """Test that transitive properties are correctly annotated"""
    VOCAB = vocab_namespace

    # Check manager property is transitive
    assert (VOCAB.manager, RDF.type, OWL.TransitiveProperty) in rdf_graph


def test_ontology_functional_property(rdf_graph, vocab_namespace):
    """Test that functional properties are correctly annotated"""
    VOCAB = vocab_namespace

    # Check age property is functional
    assert (VOCAB.age, RDF.type, OWL.FunctionalProperty) in rdf_graph

    # Check employee_id property is functional
    assert (VOCAB.employee_id, RDF.type, OWL.FunctionalProperty) in rdf_graph


def test_ontology_inverse_of_property(rdf_graph, vocab_namespace):
    """Test that inverse properties are correctly annotated"""
    VOCAB = vocab_namespace

    # Check head property is inverse of head_of
    assert (VOCAB.head, OWL.inverseOf, VOCAB.head_of) in rdf_graph

    # Check vice_head property is inverse of vice_head_of
    assert (VOCAB.vice_head, OWL.inverseOf, VOCAB.vice_head_of) in rdf_graph


def test_ontology_equivalent_property(rdf_graph, vocab_namespace):
    """Test that equivalent properties are correctly annotated"""
    VOCAB = vocab_namespace

    # Check related_project property is equivalent to another property
    # This test is not applicable as equivalentProperty is not used in TestModel
    pass

    """Test that inverse functional properties are correctly annotated"""
    VOCAB = vocab_namespace

    # Check employee_id property is inverse functional
    assert (VOCAB.employee_id, RDF.type, OWL.InverseFunctionalProperty) in rdf_graph


def test_ontology_property_type(rdf_graph, vocab_namespace):
    """Test that properties are either owl:ObjectProperty or owl:DatatypeProperty (default)"""
    VOCAB = vocab_namespace

    # Relation fields should be ObjectProperty
    assert (VOCAB.manager, RDF.type, OWL.ObjectProperty) in rdf_graph
    assert (VOCAB.department, RDF.type, OWL.ObjectProperty) in rdf_graph

    # Regular fields should be DatatypeProperty
    assert (VOCAB.name, RDF.type, OWL.DatatypeProperty) in rdf_graph
    assert (VOCAB.age, RDF.type, OWL.DatatypeProperty) in rdf_graph
    assert (VOCAB.employee_id, RDF.type, OWL.DatatypeProperty) in rdf_graph


def test_ontology_class_descriptions(rdf_graph, vocab_namespace):
    """Test that class rdfs comment is class docstring if present (default)"""
    VOCAB = vocab_namespace

    # Check Person rdfs comment
    person_comments = list(rdf_graph.objects(VOCAB.Person, RDFS.comment))
    assert len(person_comments) == 1
    assert str(person_comments[0]) == "A person, subclass of Entity"

    # Check Employee rdfs comment
    employee_comments = list(rdf_graph.objects(VOCAB.Employee, RDFS.comment))
    assert len(employee_comments) == 1
    assert str(employee_comments[0]) == "An employee, subclass of Person"

    # Check Manager rdfs comment
    manager_comments = list(rdf_graph.objects(VOCAB.Manager, RDFS.comment))
    assert len(manager_comments) == 1
    assert str(manager_comments[0]) == "A manager, subclass of Employee"

    # Check Department rdfs comment
    department_comments = list(rdf_graph.objects(VOCAB.Department, RDFS.comment))
    assert len(department_comments) == 1
    assert str(department_comments[0]) == "A department, subclass of Entity"

    # Check Company rdfs comment (should have no comment)
    company_comments = list(rdf_graph.objects(VOCAB.Company, RDFS.comment))
    assert len(company_comments) == 0


def test_ontology_property_descriptions(rdf_graph, vocab_namespace):
    """
    Test that property rdfs comment is field description if present (default),
    unless property is defined in multiple ontology classes
    """
    VOCAB = vocab_namespace

    # Check manager property rdfs comment
    manager_comments = list(rdf_graph.objects(VOCAB.manager, RDFS.comment))
    assert len(manager_comments) == 1
    assert str(manager_comments[0]) == "Link to manager"

    # Check name property rdfs comment is not present
    name_comments = list(rdf_graph.objects(VOCAB.name, RDFS.comment))
    assert len(name_comments) == 0

    # Check age property rdfs comment
    age_comments = list(rdf_graph.objects(VOCAB.age, RDFS.comment))
    assert len(age_comments) == 1
    assert str(age_comments[0]) == "Person's age in years"

    # Check department property rdfs comment
    dept_comments = list(rdf_graph.objects(VOCAB.department, RDFS.comment))
    assert len(dept_comments) == 1
    assert str(dept_comments[0]) == "Department IRI"

    # Check company property rdfs comment
    company_comments = list(rdf_graph.objects(VOCAB.company, RDFS.comment))
    assert len(company_comments) == 0


def test_ontology_property_domains(rdf_graph, vocab_namespace):
    """
    Test that properties have defining class as rdfs domain (default)
    unless property is defined in multiple ontology classes
    """
    VOCAB = vocab_namespace

    # Check name property domain is not set
    name_domains = list(rdf_graph.objects(VOCAB.name, RDFS.domain))
    assert len(name_domains) == 0

    # Check age property domain
    age_domains = list(rdf_graph.objects(VOCAB.age, RDFS.domain))
    assert len(age_domains) == 1
    assert age_domains[0] == VOCAB.Person

    # Check employee_id property domain
    employee_id_domains = list(rdf_graph.objects(VOCAB.employee_id, RDFS.domain))
    assert len(employee_id_domains) == 1
    assert employee_id_domains[0] == VOCAB.Employee

    # Check department property domain
    department_domains = list(rdf_graph.objects(VOCAB.department, RDFS.domain))
    assert len(department_domains) == 1
    assert department_domains[0] == VOCAB.Employee


def test_ontology_property_range(rdf_graph, vocab_namespace):
    """Test that rdfs:range is correctly set from Annotated metadata"""
    VOCAB = vocab_namespace

    # Check manager property range
    manager_ranges = list(rdf_graph.objects(VOCAB.manager, RDFS.range))
    assert len(manager_ranges) == 1
    assert manager_ranges[0] == VOCAB.Manager

    # Check department property range
    dept_ranges = list(rdf_graph.objects(VOCAB.department, RDFS.range))
    assert len(dept_ranges) == 1
    assert dept_ranges[0] == VOCAB.Department


def test_optional_fields_are_in_ontology(rdf_graph, vocab_namespace):
    """Test that optional fields (with default=None) are still included in ontology"""
    VOCAB = vocab_namespace

    # age is Optional[int] with default=None
    assert (VOCAB.age, RDF.type, OWL.DatatypeProperty) in rdf_graph

    # manager is Optional[Relation] with default=None
    assert (VOCAB.manager, RDF.type, OWL.ObjectProperty) in rdf_graph

    # department is Optional[Relation] with default=None
    assert (VOCAB.department, RDF.type, OWL.ObjectProperty) in rdf_graph


def test_no_orphaned_properties(rdf_graph, vocab_namespace):
    """Test that all properties that are not defined multiple times have at least a domain"""
    VOCAB = vocab_namespace
    datatype_properties = list(rdf_graph.subjects(RDF.type, OWL.DatatypeProperty))
    object_properties = list(rdf_graph.subjects(RDF.type, OWL.ObjectProperty))
    all_properties = datatype_properties + object_properties

    for prop in all_properties:
        domains = list(rdf_graph.objects(prop, RDFS.domain))
        if prop == VOCAB.name:  # Name is defined multiple times
            continue
        assert len(domains) >= 1, f"Property {prop} has no domain"
