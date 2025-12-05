import pytest
from pydantic import Field
from pyshacl import validate
from rdflib import RDF, Graph, Namespace
from rdflib.namespace import SH, XSD

from pydontology import JSONLDGraph


@pytest.fixture
def shacl_graph(TestModel):
    """Fixture providing the generated SHACL graph"""
    return TestModel.shacl_graph()


@pytest.fixture
def shacl_graph_json(shacl_graph):
    """Fixture returning the SHACL graph as json-ld"""
    return shacl_graph.model_dump_json(exclude_none=True, indent=2)


@pytest.fixture
def rdf_graph(shacl_graph_json):
    """Fixture returning the SHACL graph as an rdflib Graph"""
    g = Graph()
    g.parse(data=shacl_graph_json, format="json-ld")

    print(shacl_graph_json)
    return g


@pytest.fixture
def vocab_ns():
    """Fixture providing the vocabulary namespace"""
    return Namespace("http://example.com/vocab/")


def test_shacl_graph_returns_jsonld_graph(shacl_graph):
    """Test that shacl_graph returns a JSONLDGraph instance"""
    assert isinstance(shacl_graph, JSONLDGraph)


def test_rdflib_can_parse_shacl_graph(rdf_graph):
    """Test that rdflib can parse the SHACL graph and it contains triples"""
    assert len(rdf_graph) > 0


def test_shacl_context_structure(shacl_graph):
    """Test that SHACL graph has correct context structure"""
    shacl_dict = shacl_graph.model_dump(by_alias=True)

    assert "@context" in shacl_dict
    assert "sh" in shacl_dict["@context"]
    assert "xsd" in shacl_dict["@context"]
    assert shacl_dict["@context"]["sh"] == "http://www.w3.org/ns/shacl#"
    assert shacl_dict["@context"]["xsd"] == "http://www.w3.org/2001/XMLSchema#"


def test_node_shapes_present(rdf_graph, vocab_ns):
    """Test that all expected node shapes are present"""
    VOCAB = vocab_ns

    # Verify all node shapes exist
    assert (VOCAB.PersonShape, RDF.type, SH.NodeShape) in rdf_graph
    assert (VOCAB.EmployeeShape, RDF.type, SH.NodeShape) in rdf_graph
    assert (VOCAB.ManagerShape, RDF.type, SH.NodeShape) in rdf_graph

    # Count total node shapes (should be exactly 4)
    node_shapes = list(rdf_graph.subjects(RDF.type, SH.NodeShape))
    assert len(node_shapes) == 4


def test_target_classes(rdf_graph, vocab_ns):
    """Test that node shapes have correct target classes"""
    VOCAB = vocab_ns

    assert (VOCAB.PersonShape, SH.targetClass, VOCAB.Person) in rdf_graph
    assert (VOCAB.EmployeeShape, SH.targetClass, VOCAB.Employee) in rdf_graph
    assert (VOCAB.ManagerShape, SH.targetClass, VOCAB.Manager) in rdf_graph
    assert (VOCAB.DepartmentShape, SH.targetClass, VOCAB.Department) in rdf_graph


def test_property_shapes_count(rdf_graph, vocab_ns):
    """Test that node shapes have correct number of property shapes"""
    VOCAB = vocab_ns

    # PersonShape should have 2 properties: name, age
    person_properties = list(rdf_graph.objects(VOCAB.PersonShape, SH.property))
    assert len(person_properties) == 2

    # EmployeeShape should have 5 properties: name, age, employee_id, manager
    employee_properties = list(rdf_graph.objects(VOCAB.EmployeeShape, SH.property))
    assert len(employee_properties) == 4

    # ManagerShape should have 6 properties: all inherited + department
    manager_properties = list(rdf_graph.objects(VOCAB.ManagerShape, SH.property))
    assert len(manager_properties) == 5


def test_datatype_constraints(rdf_graph, vocab_ns):
    """Test that datatype constraints are correctly set"""
    VOCAB = vocab_ns

    # Get PersonShape properties
    person_properties = list(rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # Find name property and verify datatype
    for prop_shape in person_properties:
        path = rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.name:
            datatype = rdf_graph.value(prop_shape, SH.datatype)
            assert datatype == XSD.string
            break

    # Find age property and verify datatype
    for prop_shape in person_properties:
        path = rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.age:
            datatype = rdf_graph.value(prop_shape, SH.datatype)
            assert datatype == XSD.integer
            break


def test_string_length_constraints(rdf_graph, vocab_ns):
    """Test that string length constraints are correctly set"""
    VOCAB = vocab_ns

    person_properties = list(rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # Find name property and verify length constraints
    for prop_shape in person_properties:
        path = rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.name:
            min_length = rdf_graph.value(prop_shape, SH.minLength)
            max_length = rdf_graph.value(prop_shape, SH.maxLength)
            assert int(min_length) == 1
            assert int(max_length) == 100
            break


def test_numeric_constraints(rdf_graph, vocab_ns):
    """Test that numeric constraints are correctly set"""
    VOCAB = vocab_ns

    person_properties = list(rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # Find age property and verify numeric constraints
    for prop_shape in person_properties:
        path = rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.age:
            min_inclusive = rdf_graph.value(prop_shape, SH.minInclusive)
            max_inclusive = rdf_graph.value(prop_shape, SH.maxInclusive)
            assert float(min_inclusive) == 0.0
            assert float(max_inclusive) == 150.0
            break


def test_cardinality_constraints_required(rdf_graph, vocab_ns):
    """Test that required fields have minCount = 1"""
    VOCAB = vocab_ns

    person_properties = list(rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # name is required, should have minCount = 1
    for prop_shape in person_properties:
        path = rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.name:
            min_count = rdf_graph.value(prop_shape, SH.minCount)
            assert int(min_count) == 1
            break


def test_cardinality_constraints_optional(rdf_graph, vocab_ns):
    """Test that optional fields don't have minCount"""
    VOCAB = vocab_ns

    person_properties = list(rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # age is optional, should not have minCount
    for prop_shape in person_properties:
        path = rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.age:
            min_count = rdf_graph.value(prop_shape, SH.minCount)
            assert min_count is None
            break


def test_max_count_constraint(rdf_graph, vocab_ns):
    """Test that maxCount annotation is applied"""
    VOCAB = vocab_ns

    employee_properties = list(rdf_graph.objects(VOCAB.EmployeeShape, SH.property))

    # manager has maxCount = 1
    for prop_shape in employee_properties:
        path = rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.manager:
            max_count = rdf_graph.value(prop_shape, SH.maxCount)
            assert int(max_count) == 1
            break


def test_relation_node_kind(rdf_graph, vocab_ns):
    """Test that relation fields have sh:nodeKind sh:IRI"""
    VOCAB = vocab_ns

    employee_properties = list(rdf_graph.objects(VOCAB.EmployeeShape, SH.property))

    # manager is a Relation, should have nodeKind = sh:IRI
    for prop_shape in employee_properties:
        path = rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.manager:
            node_kind = rdf_graph.value(prop_shape, SH.nodeKind)
            assert node_kind == SH.IRI
            break


def test_relation_class_constraint(rdf_graph, vocab_ns):
    """Test that relation fields have sh:class constraint"""
    VOCAB = vocab_ns

    employee_properties = list(rdf_graph.objects(VOCAB.EmployeeShape, SH.property))

    # manager should have sh:class Manager
    for prop_shape in employee_properties:
        path = rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.manager:
            shacl_class = rdf_graph.value(prop_shape, SH["class"])
            assert shacl_class == VOCAB.Manager
            break


def test_property_shape_has_name(rdf_graph, vocab_ns):
    """Test that property shapes have sh:name"""
    VOCAB = vocab_ns

    person_properties = list(rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # All property shapes should have sh:name
    for prop_shape in person_properties:
        name = rdf_graph.value(prop_shape, SH.name)
        assert name is not None


def test_property_shape_has_description(rdf_graph, vocab_ns):
    """Test that property shapes have sh:description"""
    VOCAB = vocab_ns

    person_properties = list(rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # Find name property and verify it has description
    for prop_shape in person_properties:
        path = rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.name:
            description = rdf_graph.value(prop_shape, SH.description)
            assert description is not None
            assert str(description) == "Person's name"
            break


def test_no_duplicate_triples(rdf_graph):
    """Test that there are no duplicate triples in the SHACL graph"""
    triples = list(rdf_graph)
    unique_triples = set(triples)
    assert len(triples) == len(unique_triples), "Graph contains duplicate triples"


def test_pyshacl_validates_valid_data(shacl_graph_json):
    """Test that pyshacl validates conforming data"""
    # Create valid data graph
    data_graph_json = """
    {
        "@context": {
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/"
        },
        "@graph": [
            {
                "@id": "person1",
                "@type": "Person",
                "name": "John Doe",
                "age": 30,
                "email": "john.doe@example.com"
            }
        ]
    }
    """

    data_g = Graph()
    data_g.parse(data=data_graph_json, format="json-ld")

    shacl_g = Graph()
    shacl_g.parse(data=shacl_graph_json, format="json-ld")

    # Validate
    conforms, results_graph, results_text = validate(
        data_g, shacl_graph=shacl_g, inference="rdfs", abort_on_first=False
    )

    assert conforms, f"Validation failed: {results_text}"


def test_pyshacl_detects_missing_required_field(shacl_graph_json):
    """Test that pyshacl detects missing required fields"""
    # Create invalid data graph (missing required 'name' field)
    data_graph_json = """
    {
        "@context": {
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/"
        },
        "@graph": [
            {
                "@id": "person1",
                "@type": "Person",
                "age": 30
            }
        ]
    }
    """

    data_g = Graph()
    data_g.parse(data=data_graph_json, format="json-ld")

    shacl_g = Graph()
    shacl_g.parse(data=shacl_graph_json, format="json-ld")

    # Validate
    conforms, results_graph, results_text = validate(
        data_g, shacl_graph=shacl_g, inference="rdfs", abort_on_first=False
    )

    assert not conforms, "Validation should fail for missing required field"


def test_pyshacl_detects_numeric_constraint_violation(shacl_graph_json):
    """Test that pyshacl detects numeric constraint violations"""
    # Create invalid data graph (age out of range)
    data_graph_json = """
    {
        "@context": {
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/"
        },
        "@graph": [
            {
                "@id": "person1",
                "@type": "Person",
                "name": "John Doe",
                "age": 200
            }
        ]
    }
    """

    data_g = Graph()
    data_g.parse(data=data_graph_json, format="json-ld")

    shacl_g = Graph()
    shacl_g.parse(data=shacl_graph_json, format="json-ld")

    # Validate
    conforms, results_graph, results_text = validate(
        data_g, shacl_graph=shacl_g, inference="rdfs", abort_on_first=False
    )

    assert not conforms, "Validation should fail for numeric constraint violation"


def test_pyshacl_detects_string_length_violation(shacl_graph_json):
    """Test that pyshacl detects string length violations"""
    # Create invalid data graph (name too long)
    data_graph_json = """
    {
        "@context": {
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/"
        },
        "@graph": [
            {
                "@id": "person1",
                "@type": "Person",
                "name": "a very long name that exceeds the maximum length constraint of one hundred characters which should fail"
            }
        ]
    }
    """

    data_g = Graph()
    data_g.parse(data=data_graph_json, format="json-ld")

    shacl_g = Graph()
    shacl_g.parse(data=shacl_graph_json, format="json-ld")

    # Validate
    conforms, results_graph, results_text = validate(
        data_g, shacl_graph=shacl_g, inference="rdfs", abort_on_first=False
    )

    assert not conforms, "Validation should fail for string length violation"


def test_pyshacl_validates_employee_with_manager(shacl_graph_json):
    """Test that pyshacl validates employee with valid manager reference"""
    # Create valid data graph with employee and manager
    data_graph_json = """
    {
        "@context": {
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/"
        },
        "@graph": [
            {
            "@id": "manager1",
                "@type": "Manager",
                "name": "Jane Smith",
                "employee_id": "E001",
                "department": {"@id": "Engineering"}
            },
            {
            "@id": "employee1",
                "@type": "Employee",
                "name": "John Doe",
                "employee_id": "E002",
                "manager": {"@id": "manager1"}
            }
        ]
    }
    """

    data_g = Graph()
    data_g.parse(data=data_graph_json, format="json-ld")

    shacl_g = Graph()
    shacl_g.parse(data=shacl_graph_json, format="json-ld")

    # Validate
    conforms, results_graph, results_text = validate(
        data_g, shacl_graph=shacl_g, inference="rdfs", abort_on_first=False
    )

    assert conforms, f"Validation failed: {results_text}"
