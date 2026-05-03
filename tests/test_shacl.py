import pytest
from pyshacl import validate
from rdflib import RDF, Dataset, Graph, Namespace
from rdflib.namespace import SH, XSD

from pydontology.pydontology import BaseContext, JSONLDGraph


@pytest.fixture
def shacl_graph(TestModel):
    """Fixture providing the generated SHACL graph"""
    return TestModel.shacl_graph()


@pytest.fixture
def shacl_graph_json(shacl_graph):
    """Fixture returning the SHACL graph as json-ld"""
    return shacl_graph.model_dump_json(exclude_none=True, indent=2)


@pytest.fixture
def default_context():
    "Fixture returning the default context used in custom jsonld documents below"
    context = BaseContext().model_dump_json(exclude_none=True, indent=2)
    return context


@pytest.fixture
def sh_rdf_graph(shacl_graph_json):
    """Fixture returning the SHACL graph as an rdflib Graph"""
    ds = Dataset()
    ds.parse(data=shacl_graph_json, format="json-ld")

    return ds


@pytest.fixture
def vocab_namespace():
    """Fixture providing the vocabulary namespace"""
    return Namespace(BaseContext().vocab)


def test_shacl_graph_returns_jsonld_graph(shacl_graph):
    """Test that shacl_graph returns a JSONLDGraph instance"""
    assert isinstance(shacl_graph, JSONLDGraph)


def test_rdflib_can_parse_shacl_graph(sh_rdf_graph):
    """Test that rdflib can parse the SHACL graph and it contains triples"""
    assert len(sh_rdf_graph) > 0


def test_shacl_context_structure(shacl_graph):
    """Test that SHACL graph has correct context structure"""
    shacl_dict = shacl_graph.model_dump(by_alias=True)

    assert "@context" in shacl_dict
    assert "sh" in shacl_dict["@context"]
    assert "xsd" in shacl_dict["@context"]
    assert shacl_dict["@context"]["sh"] == "http://www.w3.org/ns/shacl#"
    assert shacl_dict["@context"]["xsd"] == "http://www.w3.org/2001/XMLSchema#"


def test_node_shapes_present(sh_rdf_graph, vocab_namespace):
    """Test that all expected node shapes are present"""
    VOCAB = vocab_namespace

    # Verify all node shapes exist
    assert (VOCAB.PersonShape, RDF.type, SH.NodeShape) in sh_rdf_graph, (
        "PersonShape not present"
    )
    assert (VOCAB.EmployeeShape, RDF.type, SH.NodeShape) in sh_rdf_graph, (
        "EmployeeShape not present"
    )
    assert (VOCAB.ManagerShape, RDF.type, SH.NodeShape) in sh_rdf_graph, (
        "ManagerShape not present"
    )
    assert (VOCAB.DepartmentShape, RDF.type, SH.NodeShape) in sh_rdf_graph, (
        "DepartmentShape not present"
    )
    assert (VOCAB.CompanyShape, RDF.type, SH.NodeShape) in sh_rdf_graph, (
        "CompanyShape not present"
    )

    # Count total node shapes (should be exactly 5)
    node_shapes = list(sh_rdf_graph.subjects(RDF.type, SH.NodeShape))
    assert len(node_shapes) == 5


def test_target_classes(sh_rdf_graph, vocab_namespace):
    """Test that node shapes have correct target classes"""
    VOCAB = vocab_namespace

    assert (VOCAB.PersonShape, SH.targetClass, VOCAB.Person) in sh_rdf_graph
    assert (VOCAB.EmployeeShape, SH.targetClass, VOCAB.Employee) in sh_rdf_graph
    assert (VOCAB.ManagerShape, SH.targetClass, VOCAB.Manager) in sh_rdf_graph
    assert (VOCAB.DepartmentShape, SH.targetClass, VOCAB.Department) in sh_rdf_graph
    assert (VOCAB.CompanyShape, SH.targetClass, VOCAB.Company) in sh_rdf_graph


def test_property_shapes_count(sh_rdf_graph, vocab_namespace):
    """Test that node shapes have correct number of property shapes"""
    VOCAB = vocab_namespace

    # PersonShape should have 3 properties
    person_properties = list(sh_rdf_graph.objects(VOCAB.PersonShape, SH.property))
    assert len(person_properties) == 3

    # EmployeeShape should have 4 properties
    employee_properties = list(sh_rdf_graph.objects(VOCAB.EmployeeShape, SH.property))
    assert len(employee_properties) == 4

    # ManagerShape should have 2 properties (no SHACL annotation but two Relations):
    manager_properties = list(sh_rdf_graph.objects(VOCAB.ManagerShape, SH.property))
    assert len(manager_properties) == 2

    # DepartmentShape should have 1 property: name, head, vice_head
    dept_properties = list(sh_rdf_graph.objects(VOCAB.DepartmentShape, SH.property))
    assert len(dept_properties) == 3


def test_datatype_constraints(sh_rdf_graph, vocab_namespace):
    """Test that datatype constraints are correctly set"""
    VOCAB = vocab_namespace

    # Get PersonShape properties
    person_properties = list(sh_rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # Find name property and verify datatype
    for prop_shape in person_properties:
        path = sh_rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.name:
            datatype = sh_rdf_graph.value(prop_shape, SH.datatype)
            assert datatype == XSD.string
            break

    # Find age property and verify datatype
    for prop_shape in person_properties:
        path = sh_rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.age:
            datatype = sh_rdf_graph.value(prop_shape, SH.datatype)
            assert datatype == XSD.integer
            break


def test_string_length_constraints(sh_rdf_graph, vocab_namespace):
    """Test that string length constraints are correctly set"""
    VOCAB = vocab_namespace

    person_properties = list(sh_rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # Find name property and verify length constraints
    for prop_shape in person_properties:
        path = sh_rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.name:
            min_length = sh_rdf_graph.value(prop_shape, SH.minLength)
            max_length = sh_rdf_graph.value(prop_shape, SH.maxLength)
            assert int(min_length) == 1
            assert int(max_length) == 100
            break


def test_numeric_constraints(sh_rdf_graph, vocab_namespace):
    """Test that numeric constraints are correctly set"""
    VOCAB = vocab_namespace

    person_properties = list(sh_rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # Find age property and verify numeric constraints
    for prop_shape in person_properties:
        path = sh_rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.age:
            min_inclusive = sh_rdf_graph.value(prop_shape, SH.minInclusive)
            max_inclusive = sh_rdf_graph.value(prop_shape, SH.maxInclusive)
            assert float(min_inclusive) == 0.0
            assert float(max_inclusive) == 150.0
            break


def test_cardinality_constraints_required(sh_rdf_graph, vocab_namespace):
    """Test that required fields have minCount = 1"""
    VOCAB = vocab_namespace

    person_properties = list(sh_rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # name is required, should have minCount = 1
    for prop_shape in person_properties:
        path = sh_rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.name:
            min_count = sh_rdf_graph.value(prop_shape, SH.minCount)
            assert int(min_count) == 1
            break


def test_cardinality_constraints_optional(sh_rdf_graph, vocab_namespace):
    """Test that optional fields don't have minCount"""
    VOCAB = vocab_namespace

    person_properties = list(sh_rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # age is optional, should not have minCount
    for prop_shape in person_properties:
        path = sh_rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.age:
            min_count = sh_rdf_graph.value(prop_shape, SH.minCount)
            assert min_count is None
            break


def test_max_count_constraint(sh_rdf_graph, vocab_namespace):
    """Test that maxCount annotation is applied"""
    VOCAB = vocab_namespace

    employee_properties = list(sh_rdf_graph.objects(VOCAB.EmployeeShape, SH.property))

    # manager has maxCount = 1
    for prop_shape in employee_properties:
        path = sh_rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.manager:
            max_count = sh_rdf_graph.value(prop_shape, SH.maxCount)
            assert int(max_count) == 1
            break


def test_relation_node_kind(sh_rdf_graph, vocab_namespace):
    """Test that relation fields have sh:nodeKind sh:IRI"""
    VOCAB = vocab_namespace

    employee_properties = list(sh_rdf_graph.objects(VOCAB.EmployeeShape, SH.property))

    # manager is a Relation, should have nodeKind = sh:IRI
    for prop_shape in employee_properties:
        path = sh_rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.manager:
            node_kind = sh_rdf_graph.value(prop_shape, SH.nodeKind)
            assert node_kind == SH.IRI
            break


def test_relation_class_constraint(sh_rdf_graph, vocab_namespace):
    """Test that relation fields have sh:class constraint"""
    VOCAB = vocab_namespace

    employee_properties = list(sh_rdf_graph.objects(VOCAB.EmployeeShape, SH.property))

    # manager should have sh:class Manager
    for prop_shape in employee_properties:
        path = sh_rdf_graph.value(prop_shape, SH.path)
        if path == VOCAB.manager:
            shacl_class = sh_rdf_graph.value(prop_shape, SH["class"])
            assert shacl_class == VOCAB.Manager
            break


def test_property_shape_has_name(sh_rdf_graph, vocab_namespace):
    """Test that property shapes have sh:name"""
    VOCAB = vocab_namespace

    person_properties = list(sh_rdf_graph.objects(VOCAB.PersonShape, SH.property))

    # All property shapes should have sh:name
    for prop_shape in person_properties:
        name = sh_rdf_graph.value(prop_shape, SH.name)
        assert name is not None


def test_pyshacl_validates_valid_data(shacl_graph_json, data_graph):
    """Test that pyshacl validates conforming data"""
    # Create valid data graph
    data_graph_json = """
    {
        "@context": {
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/vocab/"
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

    data_ds = Dataset()
    data_ds.parse(
        data=data_graph.model_dump_json(indent=2, exclude_none=True), format="json-ld"
    )
    shacl_ds = Dataset()
    shacl_ds.parse(data=shacl_graph_json, format="json-ld")

    # Validate
    conforms, results_graph, results_text = validate(
        data_graph=data_ds, shacl_graph=shacl_ds, inference="rdfs", abort_on_first=False
    )

    assert conforms, f"Validation failed: {results_text}"


def test_pyshacl_detects_missing_required_field(shacl_graph_json):
    """Test that pyshacl detects missing required fields"""
    # Create invalid data graph (missing required 'name' field)
    data_graph_json = """
    {
        "@context": {
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/vocab/"
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

    data_ds = Dataset()
    data_ds.parse(data=data_graph_json, format="json-ld")
    shacl_ds = Dataset()
    shacl_ds.parse(data=shacl_graph_json, format="json-ld")

    # Validate
    conforms, results_graph, results_text = validate(
        data_ds, shacl_graph=shacl_ds, inference="rdfs", abort_on_first=False
    )

    assert not conforms, "Validation should fail for missing required field"


def test_pyshacl_detects_numeric_constraint_violation(shacl_graph_json):
    """Test that pyshacl detects numeric constraint violations"""
    # Create invalid data graph (age out of range)
    data_graph_json = """
    {
        "@context": {
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/vocab/"
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

    data_ds = Dataset()
    data_ds.parse(data=data_graph_json, format="json-ld")
    shacl_ds = Dataset()
    shacl_ds.parse(data=shacl_graph_json, format="json-ld")

    # Validate
    conforms, results_graph, results_text = validate(
        data_ds, shacl_graph=shacl_ds, inference="rdfs", abort_on_first=False
    )

    assert not conforms, "Validation should fail for numeric constraint violation"


def test_pyshacl_detects_string_length_violation(shacl_graph_json):
    """Test that pyshacl detects string length violations"""
    # Create invalid data graph (name too long)
    data_graph_json = """
    {
        "@context": {
            "@vocab": "http://example.com/vocab/",
            "@base": "http://example.com/vocab/"
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

    data_ds = Dataset()
    data_ds.parse(data=data_graph_json, format="json-ld")
    shacl_ds = Dataset()
    shacl_ds.parse(data=shacl_graph_json, format="json-ld")

    # Validate
    conforms, results_graph, results_text = validate(
        data_ds, shacl_graph=shacl_ds, inference="rdfs", abort_on_first=False
    )

    assert not conforms, "Validation should fail for string length violation"


# def test_pyshacl_validates_employee_with_manager(shacl_graph_json, default_context):
#    """Test that pyshacl validates employee with valid manager reference"""
#    # Create valid data graph with employee and manager
#    data_graph_json = """
#    {
#        "@context": {
#            "@vocab": "http://example.com/vocab/",
#            "@base": "http://example.com/vocab/",
#        },
#        "@graph": [
#            {
#                "@id": "manager1",
#                "@type": "Manager",
#                "name": "Jane Smith",
#                "employee_id": "E001",
#                "department": {"@id": "Engineering"},
#            },
#            {
#                "@id": "employee1",
#                "@type": "Employee",
#                "name": "John Doe",
#                "employee_id": "E002",
#                "manager": {"@id": "manager1"},
#                "department": {"@id": "Engineering"},
#            },
#        ],
#    }
#    """
#
#    data_ds = Dataset()
#    data_ds.parse(data=data_graph_json, format="json-ld")
#    shacl_ds = Dataset()
#    shacl_ds.parse(data=shacl_graph_json, format="json-ld")
#
#    # Validate
#    conforms, results_graph, results_text = validate(
#        data_ds, shacl_graph=shacl_ds, inference="owl", abort_on_first=False
#    )
#
#    assert conforms, f"Validation failed: {results_text}"
