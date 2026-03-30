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

    print(f"vocab_namespace: {vocab_namespace}")
    print("Triples:")
    for s, p, o in rdf_graph:
        print(s, p, p)

    # Verify all classes exist as rdfs:Class
    assert (VOCAB.Person, RDF.type, RDFS.Class) in rdf_graph
    assert (VOCAB.Employee, RDF.type, RDFS.Class) in rdf_graph
    assert (VOCAB.Manager, RDF.type, RDFS.Class) in rdf_graph
    assert (VOCAB.Department, RDF.type, RDFS.Class) in rdf_graph

    # Count total classes (should be exactly 4)
    classes = list(rdf_graph.subjects(RDF.type, RDFS.Class))
    assert len(classes) == 4


def test_ontology_inheritance(rdf_graph, vocab_namespace):
    """Test that inheritance relationships are correctly represented"""
    VOCAB = vocab_namespace

    # Employee should be subclass of Person
    assert (VOCAB.Employee, RDFS.subClassOf, VOCAB.Person) in rdf_graph

    # Manager should be subclass of Employee
    assert (VOCAB.Manager, RDFS.subClassOf, VOCAB.Employee) in rdf_graph

    # Person should be subclass of owl:Thing (Entity)
    assert (VOCAB.Person, RDFS.subClassOf, OWL.Thing) in rdf_graph

    # Department should be subclass of owl:Thing (Entity)
    assert (VOCAB.Department, RDFS.subClassOf, OWL.Thing) in rdf_graph


def test_ontology_properties_present(rdf_graph, vocab_namespace):
    """Test that all expected properties are present"""
    VOCAB = vocab_namespace

    # Get all properties (both ObjectProperty and DatatypeProperty)
    object_properties = list(rdf_graph.subjects(RDF.type, OWL.ObjectProperty))
    datatype_properties = list(rdf_graph.subjects(RDF.type, OWL.DatatypeProperty))
    all_properties = object_properties + datatype_properties

    # Should have exactly 5 properties
    assert len(all_properties) == 5

    # Verify each expected property exists
    assert VOCAB.name in all_properties
    assert VOCAB.age in all_properties
    assert VOCAB.employee_id in all_properties
    assert VOCAB.manager in all_properties
    assert VOCAB.department in all_properties


def test_ontology_property_types(rdf_graph, vocab_namespace):
    """Test that properties have correct types (ObjectProperty vs DatatypeProperty)"""
    VOCAB = vocab_namespace

    # Relation fields should be ObjectProperty
    assert (VOCAB.manager, RDF.type, OWL.ObjectProperty) in rdf_graph
    assert (VOCAB.department, RDF.type, OWL.ObjectProperty) in rdf_graph

    # Regular fields should be DatatypeProperty
    assert (VOCAB.name, RDF.type, OWL.DatatypeProperty) in rdf_graph
    assert (VOCAB.age, RDF.type, OWL.DatatypeProperty) in rdf_graph
    assert (VOCAB.employee_id, RDF.type, OWL.DatatypeProperty) in rdf_graph


def test_ontology_class_descriptions(rdf_graph, vocab_namespace):
    """Test that class descriptions are included as rdfs:comment"""
    VOCAB = vocab_namespace

    # Check Person comment
    person_comments = list(rdf_graph.objects(VOCAB.Person, RDFS.comment))
    assert len(person_comments) == 1
    assert str(person_comments[0]) == "A person, inherits from Entity"

    # Check Employee comment
    employee_comments = list(rdf_graph.objects(VOCAB.Employee, RDFS.comment))
    assert len(employee_comments) == 1
    assert str(employee_comments[0]) == "An employee, inherits from Person"

    # Check Manager comment
    manager_comments = list(rdf_graph.objects(VOCAB.Manager, RDFS.comment))
    assert len(manager_comments) == 1
    assert str(manager_comments[0]) == "A manager, inherits from Employee"

    # Check Department comment
    department_comments = list(rdf_graph.objects(VOCAB.Department, RDFS.comment))
    assert len(department_comments) == 1
    assert str(department_comments[0]) == "A department, inherits from Entity"


def test_ontology_property_descriptions(rdf_graph, vocab_namespace):
    """Test that property descriptions are included"""
    VOCAB = vocab_namespace

    # Check manager property comment
    manager_comments = list(rdf_graph.objects(VOCAB.manager, RDFS.comment))
    assert len(manager_comments) == 1
    assert str(manager_comments[0]) == "Link to manager"

    # Check name property comment (appears in both Person and Department)
    name_comments = list(rdf_graph.objects(VOCAB.name, RDFS.comment))
    assert len(name_comments) == 1
    assert str(name_comments[0]) in ["Person's name | Department's name"]

    # Check age property comment
    age_comments = list(rdf_graph.objects(VOCAB.age, RDFS.comment))
    assert len(age_comments) == 1
    assert str(age_comments[0]) == "Person's age in years"

    # Check department property comment
    dept_comments = list(rdf_graph.objects(VOCAB.department, RDFS.comment))
    assert len(dept_comments) == 1
    assert str(dept_comments[0]) == "Department IRI"


def test_ontology_property_domains(rdf_graph, vocab_namespace):
    """Test that properties have correct domain assignments"""
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
    assert department_domains[0] == VOCAB.Manager


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


def test_property_uniqueness(rdf_graph, vocab_namespace):
    """Test that each property is defined only once, even if used in multiple classes"""
    VOCAB = vocab_namespace

    # 'name' appears in both Person and Department
    # It should only have one rdf:type triple
    name_types = list(rdf_graph.objects(VOCAB.name, RDF.type))
    assert len(name_types) == 1
    assert name_types[0] == OWL.DatatypeProperty

    # It should only have one rdfs:comment
    name_comments = list(rdf_graph.objects(VOCAB.name, RDFS.comment))
    assert len(name_comments) == 1

    # It should only have no rdfs:domain
    # (rdfs:domain needs to be set explicitly for properties defined multiple times
    name_domains = list(rdf_graph.objects(VOCAB.name, RDFS.domain))
    assert len(name_domains) == 0


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


def test_no_duplicate_triples(rdf_graph):
    """Test that there are no duplicate triples in the graph"""
    triples = list(rdf_graph)
    unique_triples = set(triples)
    assert len(triples) == len(unique_triples), "Graph contains duplicate triples"


def test_datatype_properties_dont_have_class_ranges(rdf_graph, vocab_namespace):
    """Test that datatype properties don't have rdfs:range pointing to ontology classes"""

    # Get all datatype properties
    datatype_properties = list(rdf_graph.subjects(RDF.type, OWL.DatatypeProperty))

    # Get all classes in the ontology
    ontology_classes = list(rdf_graph.subjects(RDF.type, RDFS.Class))

    for prop in datatype_properties:
        ranges = list(rdf_graph.objects(prop, RDFS.range))
        for range_val in ranges:
            # Range should not be one of our ontology classes
            assert range_val not in ontology_classes, (
                f"Datatype property {prop} has range pointing to class {range_val}"
            )


def test_object_properties_have_class_ranges(rdf_graph, vocab_namespace):
    """Test that object properties have rdfs:range pointing to classes"""
    VOCAB = vocab_namespace

    # manager should have range Manager
    manager_ranges = list(rdf_graph.objects(VOCAB.manager, RDFS.range))
    assert len(manager_ranges) == 1
    assert manager_ranges[0] == VOCAB.Manager
    assert (manager_ranges[0], RDF.type, RDFS.Class) in rdf_graph

    # department should have range Department
    dept_ranges = list(rdf_graph.objects(VOCAB.department, RDFS.range))
    assert len(dept_ranges) == 1
    assert dept_ranges[0] == VOCAB.Department
    assert (dept_ranges[0], RDF.type, RDFS.Class) in rdf_graph
