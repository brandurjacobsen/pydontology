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
def vocab_ns():  # vocab namespace
    """Fixture providing the vocabulary namespace"""
    return Namespace("http://example.com/vocab/")


def test_returns_jsonld_graph(onto_graph):
    """Test that onto_graph returns a JSONLDGraph instance"""
    assert isinstance(onto_graph, JSONLDGraph)


def test_rdflib_can_parse_rdf_graph(rdf_graph):
    """Test that rdflib can parse the ontology graph and it contains triples"""
    assert len(rdf_graph) > 0


def test_ontology_classes_present(rdf_graph, vocab_ns):
    """Test that all expected classes are present in ontology graph"""
    VOCAB = vocab_ns

    # Verify all classes exist as rdfs:Class
    assert (VOCAB.Person, RDF.type, RDFS.Class) in rdf_graph
    assert (VOCAB.Employee, RDF.type, RDFS.Class) in rdf_graph
    assert (VOCAB.Manager, RDF.type, RDFS.Class) in rdf_graph
    assert (VOCAB.Department, RDF.type, RDFS.Class) in rdf_graph

    # Count total classes (should be exactly 4)
    classes = list(rdf_graph.subjects(RDF.type, RDFS.Class))
    assert len(classes) == 4


def test_ontology_inheritance(rdf_graph, vocab_ns):
    """Test that inheritance relationships are correctly represented"""
    VOCAB = vocab_ns

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


def test_ontology_class_descriptions(rdf_graph, vocab_ns):
    """Test that class descriptions are included as rdfs:comment"""
    VOCAB = vocab_ns

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


def test_ontology_properties_present(rdf_graph, vocab_ns):
    """Test that all expected properties are present"""
    VOCAB = vocab_ns

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


def test_ontology_property_types(rdf_graph, vocab_ns):
    """Test that properties have correct types (ObjectProperty vs DatatypeProperty)"""
    VOCAB = vocab_ns

    # Relation fields should be ObjectProperty
    assert (VOCAB.manager, RDF.type, OWL.ObjectProperty) in rdf_graph
    assert (VOCAB.department, RDF.type, OWL.ObjectProperty) in rdf_graph

    # Regular fields should be DatatypeProperty
    assert (VOCAB.name, RDF.type, OWL.DatatypeProperty) in rdf_graph
    assert (VOCAB.age, RDF.type, OWL.DatatypeProperty) in rdf_graph
    assert (VOCAB.employee_id, RDF.type, OWL.DatatypeProperty) in rdf_graph


def test_ontology_property_descriptions(rdf_graph, vocab_ns):
    """Test that property descriptions are included"""
    VOCAB = vocab_ns

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


def test_ontology_property_domains(rdf_graph, vocab_ns):
    """Test that properties have correct domain assignments"""
    VOCAB = vocab_ns

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


def test_ontology_property_range(rdf_graph, vocab_ns):
    """Test that rdfs:range is correctly set from Annotated metadata"""
    VOCAB = vocab_ns

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


# Point 2: Edge Cases and Constraints


def test_optional_fields_are_in_ontology(rdf_graph, vocab_ns):
    """Test that optional fields (with default=None) are still included in ontology"""
    VOCAB = vocab_ns

    # age is Optional[int] with default=None
    assert (VOCAB.age, RDF.type, OWL.DatatypeProperty) in rdf_graph

    # manager is Optional[Relation] with default=None
    assert (VOCAB.manager, RDF.type, OWL.ObjectProperty) in rdf_graph

    # department is Optional[Relation] with default=None
    assert (VOCAB.department, RDF.type, OWL.ObjectProperty) in rdf_graph


def test_property_uniqueness(rdf_graph, vocab_ns):
    """Test that each property is defined only once, even if used in multiple classes"""
    VOCAB = vocab_ns

    # 'name' appears in both Person and Department
    # It should only have one rdf:type triple
    name_types = list(rdf_graph.objects(VOCAB.name, RDF.type))
    assert len(name_types) == 1
    assert name_types[0] == OWL.DatatypeProperty

    # It should only have one rdfs:comment
    name_comments = list(rdf_graph.objects(VOCAB.name, RDFS.comment))
    assert len(name_comments) == 1

    # It should only have one rdfs:domain
    name_domains = list(rdf_graph.objects(VOCAB.name, RDFS.domain))
    assert len(name_domains) == 1


def test_no_orphaned_properties(rdf_graph):
    """Test that all properties have at least a domain"""
    datatype_properties = list(rdf_graph.subjects(RDF.type, OWL.DatatypeProperty))
    object_properties = list(rdf_graph.subjects(RDF.type, OWL.ObjectProperty))
    all_properties = datatype_properties + object_properties

    for prop in all_properties:
        domains = list(rdf_graph.objects(prop, RDFS.domain))
        assert len(domains) >= 1, f"Property {prop} has no domain"


def test_no_duplicate_triples(rdf_graph):
    """Test that there are no duplicate triples in the graph"""
    triples = list(rdf_graph)
    unique_triples = set(triples)
    assert len(triples) == len(unique_triples), "Graph contains duplicate triples"


def test_datatype_properties_dont_have_class_ranges(rdf_graph, vocab_ns):
    """Test that datatype properties don't have rdfs:range pointing to ontology classes"""
    VOCAB = vocab_ns

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


def test_object_properties_have_class_ranges(rdf_graph, vocab_ns):
    """Test that object properties have rdfs:range pointing to classes"""
    VOCAB = vocab_ns

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


# Point 7: SPARQL Queries


def test_sparql_class_hierarchy_query(rdf_graph):
    """Test querying the class hierarchy using SPARQL"""
    query = """
        SELECT ?subclass ?superclass
        WHERE {
            ?subclass rdfs:subClassOf ?superclass .
        }
    """
    results = list(rdf_graph.query(query))
    # Should have exactly 2 subclass relationships:
    # Employee -> Person, Manager -> Employee
    assert len(results) == 2


def test_sparql_find_all_object_properties(rdf_graph):
    """Test finding all object properties via SPARQL"""
    query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?prop
        WHERE {
            ?prop a owl:ObjectProperty .
        }
    """
    results = list(rdf_graph.query(query))
    # Should have exactly 2 object properties: manager, department
    assert len(results) == 2


def test_sparql_find_all_datatype_properties(rdf_graph):
    """Test finding all datatype properties via SPARQL"""
    query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?prop
        WHERE {
            ?prop a owl:DatatypeProperty .
        }
    """
    results = list(rdf_graph.query(query))
    # Should have exactly 3 datatype properties: name, age, employee_id
    assert len(results) == 3


def test_sparql_find_properties_by_domain(rdf_graph, vocab_ns):
    """Test finding properties by their domain using SPARQL"""
    VOCAB = vocab_ns

    query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?prop
        WHERE {{
            ?prop rdfs:domain <{VOCAB.Employee}> .
        }}
    """
    results = list(rdf_graph.query(query))
    # employee_id has domain Employee
    assert len(results) == 1


def test_sparql_find_classes_with_comments(rdf_graph):
    """Test finding all classes that have rdfs:comment using SPARQL"""
    query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?class ?comment
        WHERE {
            ?class a rdfs:Class .
            ?class rdfs:comment ?comment .
        }
    """
    results = list(rdf_graph.query(query))
    # All 4 classes should have comments
    assert len(results) == 4


def test_sparql_transitive_subclass_query(rdf_graph, vocab_ns):
    """Test transitive subclass relationships using SPARQL property paths"""
    VOCAB = vocab_ns

    query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?subclass
        WHERE {{
            ?subclass rdfs:subClassOf+ <{VOCAB.Person}> .
        }}
    """
    results = list(rdf_graph.query(query))
    # Both Employee and Manager are transitive subclasses of Person
    assert len(results) == 2

    subclasses = [row[0] for row in results]
    assert VOCAB.Employee in subclasses
    assert VOCAB.Manager in subclasses


def test_sparql_count_properties_per_class(rdf_graph):
    """Test counting properties per class using SPARQL"""
    query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?class (COUNT(?prop) as ?propCount)
        WHERE {
            ?class a rdfs:Class .
            ?prop rdfs:domain ?class .
        }
        GROUP BY ?class
    """
    results = list(rdf_graph.query(query))
    # Should have results for classes that have properties with their domain
    assert len(results) > 0

    # Convert to dict for easier checking
    class_prop_counts = {str(row[0]): int(row[1]) for row in results}

    # Employee should have at least employee_id
    employee_uri = "http://example.com/vocab/Employee"
    assert employee_uri in class_prop_counts
    assert class_prop_counts[employee_uri] >= 1


def test_sparql_find_properties_with_range(rdf_graph):
    """Test finding properties that have rdfs:range defined using SPARQL"""
    query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?prop ?range
        WHERE {
            ?prop rdfs:range ?range .
        }
    """
    results = list(rdf_graph.query(query))
    # manager and department should have ranges
    assert len(results) == 2

    # Extract property-range pairs
    prop_ranges = [(str(row[0]), str(row[1])) for row in results]

    # Check that manager and department are in the results
    prop_uris = [pr[0] for pr in prop_ranges]
    assert "http://example.com/vocab/manager" in prop_uris
    assert "http://example.com/vocab/department" in prop_uris
