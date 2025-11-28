import pytest
from rdflib import Graph, Namespace, RDF, Literal
from pydontology import Entity, Relation, JSONLDGraph, RDFSAnnotation, SHACLAnnotation, make_model
from pydantic import Field
from typing import Optional, Annotated


@pytest.fixture
def person_model_with_shacl():
    """Fixture providing entity classes with SHACL annotations"""
    class Person(Entity):
        """A person entity"""
        name: Annotated[str, SHACLAnnotation.minLength(1), SHACLAnnotation.maxLength(100)] = Field(description="Person's name")
        age: Annotated[Optional[int], SHACLAnnotation.minInclusive(0), SHACLAnnotation.maxInclusive(150)] = Field(default=None, description="Person's age")
        email: Annotated[Optional[str], SHACLAnnotation.pattern(r'^[\w\.-]+@[\w\.-]+\.\w+$')] = Field(default=None, description="Email address")

    class Employee(Person):
        """An employee entity, inherits from Person"""
        employee_id: Annotated[str, SHACLAnnotation.pattern(r'^E\d{3}$')] = Field(description="Employee ID")
        manager: Annotated[Optional[Relation], RDFSAnnotation.range('Manager'), SHACLAnnotation.shclass('Manager'), SHACLAnnotation.maxCount(1)] = Field(default=None, description="Link to manager")

    class Manager(Employee):
        """A manager entity, inherits from Employee"""
        department: Annotated[str, SHACLAnnotation.minLength(1)] = Field(description="Department name")

    return make_model(Person, name="PersonModel")


def test_shacl_graph_returns_jsonld_graph(person_model_with_shacl):
    """Test that shacl_graph returns a JSONLDGraph instance"""
    shacl = person_model_with_shacl.shacl_graph()
    assert isinstance(shacl, JSONLDGraph)


def test_shacl_graph_structure(person_model_with_shacl):
    """Test that SHACL graph has correct top-level structure"""
    shacl = person_model_with_shacl.shacl_graph()
    shacl_dict = shacl.model_dump(by_alias=True)

    assert "@context" in shacl_dict
    assert "@graph" in shacl_dict
    assert "sh" in shacl_dict["@context"]
    assert "xsd" in shacl_dict["@context"]
    assert shacl_dict["@context"]["sh"] == "http://www.w3.org/ns/shacl#"
    assert shacl_dict["@context"]["xsd"] == "http://www.w3.org/2001/XMLSchema#"


def test_shacl_node_shapes_present(person_model_with_shacl):
    """Test that all expected node shapes are present"""
    shacl = person_model_with_shacl.shacl_graph()
    shacl_dict = shacl.model_dump(by_alias=True)

    node_shapes = [item for item in shacl_dict["@graph"] if item.get("@type") == "sh:NodeShape"]
    shape_names = {shape["@id"] for shape in node_shapes}

    assert len(node_shapes) == 3
    assert "PersonShape" in shape_names
    assert "EmployeeShape" in shape_names
    assert "ManagerShape" in shape_names


def test_shacl_target_classes(person_model_with_shacl):
    """Test that node shapes have correct target classes"""
    shacl = person_model_with_shacl.shacl_graph()
    shacl_dict = shacl.model_dump(by_alias=True)

    node_shapes = [item for item in shacl_dict["@graph"] if item.get("@type") == "sh:NodeShape"]

    person_shape = next(shape for shape in node_shapes if shape["@id"] == "PersonShape")
    assert person_shape["sh:targetClass"]["@id"] == "Person"

    employee_shape = next(shape for shape in node_shapes if shape["@id"] == "EmployeeShape")
    assert employee_shape["sh:targetClass"]["@id"] == "Employee"

    manager_shape = next(shape for shape in node_shapes if shape["@id"] == "ManagerShape")
    assert manager_shape["sh:targetClass"]["@id"] == "Manager"


def test_shacl_property_shapes_present(person_model_with_shacl):
    """Test that property shapes are present in node shapes"""
    shacl = person_model_with_shacl.shacl_graph()
    shacl_dict = shacl.model_dump(by_alias=True)

    node_shapes = [item for item in shacl_dict["@graph"] if item.get("@type") == "sh:NodeShape"]

    person_shape = next(shape for shape in node_shapes if shape["@id"] == "PersonShape")
    assert "sh:property" in person_shape
    assert len(person_shape["sh:property"]) == 3  # name, age, email

    employee_shape = next(shape for shape in node_shapes if shape["@id"] == "EmployeeShape")
    assert "sh:property" in employee_shape
    assert len(employee_shape["sh:property"]) == 5  # name, age, email, employee_id, manager

    manager_shape = next(shape for shape in node_shapes if shape["@id"] == "ManagerShape")
    assert "sh:property" in manager_shape
    assert len(manager_shape["sh:property"]) == 6  # all inherited + department


def test_shacl_datatype_constraints(person_model_with_shacl):
    """Test that datatype constraints are correctly set"""
    shacl = person_model_with_shacl.shacl_graph()
    shacl_dict = shacl.model_dump(by_alias=True)

    node_shapes = [item for item in shacl_dict["@graph"] if item.get("@type") == "sh:NodeShape"]
    person_shape = next(shape for shape in node_shapes if shape["@id"] == "PersonShape")

    # Find name property shape
    name_prop = next(prop for prop in person_shape["sh:property"] if prop["sh:path"]["@id"] == "name")
    assert name_prop["sh:datatype"]["@id"] == "xsd:string"

    # Find age property shape
    age_prop = next(prop for prop in person_shape["sh:property"] if prop["sh:path"]["@id"] == "age")
    assert age_prop["sh:datatype"]["@id"] == "xsd:integer"


def test_shacl_string_constraints(person_model_with_shacl):
    """Test that string length constraints are correctly set"""
    shacl = person_model_with_shacl.shacl_graph()
    shacl_dict = shacl.model_dump(by_alias=True)

    node_shapes = [item for item in shacl_dict["@graph"] if item.get("@type") == "sh:NodeShape"]
    person_shape = next(shape for shape in node_shapes if shape["@id"] == "PersonShape")

    # Find name property shape
    name_prop = next(prop for prop in person_shape["sh:property"] if prop["sh:path"]["@id"] == "name")
    assert name_prop["sh:minLength"] == 1
    assert name_prop["sh:maxLength"] == 100


def test_shacl_numeric_constraints(person_model_with_shacl):
    """Test that numeric constraints are correctly set"""
    shacl = person_model_with_shacl.shacl_graph()
    shacl_dict = shacl.model_dump(by_alias=True)

    node_shapes = [item for item in shacl_dict["@graph"] if item.get("@type") == "sh:NodeShape"]
    person_shape = next(shape for shape in node_shapes if shape["@id"] == "PersonShape")

    # Find age property shape
    age_prop = next(prop for prop in person_shape["sh:property"] if prop["sh:path"]["@id"] == "age")
    assert age_prop["sh:minInclusive"] == 0
    assert age_prop["sh:maxInclusive"] == 150


def test_shacl_pattern_constraints(person_model_with_shacl):
    """Test that pattern constraints are correctly set"""
    shacl = person_model_with_shacl.shacl_graph()
    shacl_dict = shacl.model_dump(by_alias=True)

    node_shapes = [item for item in shacl_dict["@graph"] if item.get("@type") == "sh:NodeShape"]

    person_shape = next(shape for shape in node_shapes if shape["@id"] == "PersonShape")
    email_prop = next(prop for prop in person_shape["sh:property"] if prop["sh:path"]["@id"] == "email")
    assert email_prop["sh:pattern"] == r'^[\w\.-]+@[\w\.-]+\.\w+$'

    employee_shape = next(shape for shape in node_shapes if shape["@id"] == "EmployeeShape")
    employee_id_prop = next(prop for prop in employee_shape["sh:property"] if prop["sh:path"]["@id"] == "employee_id")
    assert employee_id_prop["sh:pattern"] == r'^E\d{3}$'


def test_shacl_cardinality_constraints(person_model_with_shacl):
    """Test that cardinality constraints are correctly set"""
    shacl = person_model_with_shacl.shacl_graph()
    shacl_dict = shacl.model_dump(by_alias=True)

    node_shapes = [item for item in shacl_dict["@graph"] if item.get("@type") == "sh:NodeShape"]

    person_shape = next(shape for shape in node_shapes if shape["@id"] == "PersonShape")

    # Required field should have minCount = 1
    name_prop = next(prop for prop in person_shape["sh:property"] if prop["sh:path"]["@id"] == "name")
    assert name_prop["sh:minCount"] == 1

    # Optional field should not have minCount
    age_prop = next(prop for prop in person_shape["sh:property"] if prop["sh:path"]["@id"] == "age")
    assert "sh:minCount" not in age_prop or age_prop.get("sh:minCount") is None

    # Field with explicit maxCount annotation
    employee_shape = next(shape for shape in node_shapes if shape["@id"] == "EmployeeShape")
    manager_prop = next(prop for prop in employee_shape["sh:property"] if prop["sh:path"]["@id"] == "manager")
    assert manager_prop["sh:maxCount"] == 1


def test_shacl_relation_constraints(person_model_with_shacl):
    """Test that relation fields have correct constraints"""
    shacl = person_model_with_shacl.shacl_graph()
    shacl_dict = shacl.model_dump(by_alias=True)

    node_shapes = [item for item in shacl_dict["@graph"] if item.get("@type") == "sh:NodeShape"]
    employee_shape = next(shape for shape in node_shapes if shape["@id"] == "EmployeeShape")

    # Find manager property shape
    manager_prop = next(prop for prop in employee_shape["sh:property"] if prop["sh:path"]["@id"] == "manager")
    assert manager_prop["sh:nodeKind"] == "sh:IRI"
    assert manager_prop["sh:class"]["@id"] == "Manager"


def test_rdflib_parse_shacl_graph(person_model_with_shacl):
    """Test that rdflib can parse the SHACL graph output"""
    # Generate SHACL graph
    shacl = person_model_with_shacl.shacl_graph()

    # Serialize to JSON-LD string
    shacl_str = shacl.model_dump_json(by_alias=True, exclude_none=True)

    # Parse with rdflib
    g = Graph()
    g.parse(data=shacl_str, format='json-ld')

    # Verify we have triples
    assert len(g) > 0

    # Define namespaces
    VOCAB = Namespace("http://example.com/vocab/")
    SH = Namespace("http://www.w3.org/ns/shacl#")

    # Verify node shapes exist
    assert (VOCAB.PersonShape, RDF.type, SH.NodeShape) in g
    assert (VOCAB.EmployeeShape, RDF.type, SH.NodeShape) in g
    assert (VOCAB.ManagerShape, RDF.type, SH.NodeShape) in g

    # Verify target classes
    assert (VOCAB.PersonShape, SH.targetClass, VOCAB.Person) in g
    assert (VOCAB.EmployeeShape, SH.targetClass, VOCAB.Employee) in g
    assert (VOCAB.ManagerShape, SH.targetClass, VOCAB.Manager) in g

    # Verify property shapes exist (check that PersonShape has property shapes)
    person_shape_properties = list(g.objects(VOCAB.PersonShape, SH.property))
    assert len(person_shape_properties) == 3

    # Find the name property shape and verify constraints
    for prop_shape in person_shape_properties:
        path = g.value(prop_shape, SH.path)
        if path == VOCAB.name:
            # Check minLength constraint
            min_length = g.value(prop_shape, SH.minLength)
            assert min_length is not None
            assert int(min_length) == 1

            # Check maxLength constraint
            max_length = g.value(prop_shape, SH.maxLength)
            assert max_length is not None
            assert int(max_length) == 100

            # Check datatype
            datatype = g.value(prop_shape, SH.datatype)
            assert datatype is not None
            break

    # Find the age property shape and verify numeric constraints
    for prop_shape in person_shape_properties:
        path = g.value(prop_shape, SH.path)
        if path == VOCAB.age:
            # Check minInclusive constraint
            min_inclusive = g.value(prop_shape, SH.minInclusive)
            assert min_inclusive is not None
            assert float(min_inclusive) == 0.0

            # Check maxInclusive constraint
            max_inclusive = g.value(prop_shape, SH.maxInclusive)
            assert max_inclusive is not None
            assert float(max_inclusive) == 150.0
            break

    # Find the email property shape and verify pattern constraint
    for prop_shape in person_shape_properties:
        path = g.value(prop_shape, SH.path)
        if path == VOCAB.email:
            # Check pattern constraint
            pattern = g.value(prop_shape, SH.pattern)
            assert pattern is not None
            assert str(pattern) == r'^[\w\.-]+@[\w\.-]+\.\w+$'
            break

    # Verify employee_id pattern constraint
    employee_shape_properties = list(g.objects(VOCAB.EmployeeShape, SH.property))
    for prop_shape in employee_shape_properties:
        path = g.value(prop_shape, SH.path)
        if path == VOCAB.employee_id:
            pattern = g.value(prop_shape, SH.pattern)
            assert pattern is not None
            assert str(pattern) == r'^E\d{3}$'
            break

    # Verify manager relation constraints
    for prop_shape in employee_shape_properties:
        path = g.value(prop_shape, SH.path)
        if path == VOCAB.manager:
            # Check nodeKind
            node_kind = g.value(prop_shape, SH.nodeKind)
            assert str(node_kind) == "sh:IRI"

            # Check class constraint
            shacl_class = g.value(prop_shape, SH['class'])
            assert shacl_class == VOCAB.Manager

            # Check maxCount
            max_count = g.value(prop_shape, SH.maxCount)
            assert max_count is not None
            assert int(max_count) == 1
            break
