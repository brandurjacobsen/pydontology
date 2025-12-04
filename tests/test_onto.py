import pytest
from rdflib import OWL, RDF, RDFS, Graph, Namespace

from pydontology import JSONLDGraph

# See conftest.py for TestModel definition


@pytest.fixture
def onto_graph(TestModel):
    """Fixture providing the generated ontology graph"""
    return TestModel.ontology_graph()


@pytest.fixture
def onto_graph_json(onto_graph):
    """Returns the json-ld string of the ontology graph"""
    return onto_graph.model_dump_json(exclude_none=True)


@pytest.fixture
def rdf_graph(onto_graph_json):
    """Fixture providing the ontology as an rdflib Graph"""
    g = Graph()
    g.parse(data=onto_graph_json, format="json-ld")
    return g


@pytest.fixture
def vocab_namespace():
    """Fixture providing the vocabulary namespace"""
    return Namespace("http://example.com/vocab/")


def test_ontology_model_returns_jsonld_graph(onto_graph):
    """Test that onto_graph returns a JSONLDGraph instance"""
    assert isinstance(onto_graph, JSONLDGraph)


def test_rdflib_can_parse_ontology_graph(rdf_graph):
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
    
    # Count total classes (should be exactly 4)
    classes = list(rdf_graph.subjects(RDF.type, RDFS.Class))
    assert len(classes) == 4


def test_ontology_inheritance(rdf_graph, vocab_namespace):
    """Test that inheritance relationships are correctly represented"""
    VOCAB = vocab_namespace
    
    # Employee should inherit from Person
    assert (VOCAB.Employee, RDFS.subClassOf, VOCAB.Person) in rdf_graph
    
    # Manager should inherit from Employee
    assert (VOCAB.Manager, RDFS.subClassOf, VOCAB.Employee) in rdf_graph
    
    # Person should not have subClassOf (it inherits Entity, which is not in the ontology)
    person_subclasses = list(rdf_graph.objects(VOCAB.Person, RDFS.subClassOf))
    assert len(person_subclasses) == 0
    
    # Department should not have subClassOf (it inherits Entity, which is not in the ontology)
    department_subclasses = list(rdf_graph.objects(VOCAB.Department, RDFS.subClassOf))
    assert len(department_subclasses) == 0


def test_ontology_class_descriptions(rdf_graph, vocab_namespace):
    """Test that class descriptions are included as rdfs:comment"""
    VOCAB = vocab_namespace
    
    # Check Person comment
    person_comments = list(rdf_graph.objects(VOCAB.Person, RDFS.comment))
    assert len(person_comments) == 1
    assert str(person_comments[0]) == "A person"
    
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
    assert str(name_comments[0]) in ["Person's name", "Department name"]
    
    # Check age property comment
    age_comments = list(rdf_graph.objects(VOCAB.age, RDFS.comment))
    assert len(age_comments) == 1
    assert str(age_comments[0]) == "Person's age"
    
    # Check department property comment
    dept_comments = list(rdf_graph.objects(VOCAB.department, RDFS.comment))
    assert len(dept_comments) == 1
    assert str(dept_comments[0]) == "Department IRI"


def test_ontology_property_domains(rdf_graph, vocab_namespace):
    """Test that properties have correct domain assignments"""
    VOCAB = vocab_namespace
    
    # Check name property domain (could be Person or Department)
    name_domains = list(rdf_graph.objects(VOCAB.name, RDFS.domain))
    assert len(name_domains) == 1
    assert name_domains[0] in [VOCAB.Person, VOCAB.Department]
    
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


def test_ontology_json_structure(onto_graph):
    """Test that ontology graph has correct top-level JSON-LD structure"""
    ontology_dict = onto_graph.model_dump(by_alias=True)
    
    assert "@context" in ontology_dict
    assert "@graph" in ontology_dict
    assert "rdfs" in ontology_dict["@context"]
    assert "owl" in ontology_dict["@context"]


def test_ontology_serialization(onto_graph):
    """Test that ontology can be serialized to valid JSON-LD"""
    import json
    
    json_output = onto_graph.model_dump_json(by_alias=True, exclude_none=True)
    assert json_output is not None
    assert len(json_output) > 0
    
    # Should be valid JSON that can be parsed back
    parsed = json.loads(json_output)
    assert "@context" in parsed
    assert "@graph" in parsed
