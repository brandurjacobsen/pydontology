# Test Instructions for Issue #15: Track attributes by alias

1. **Aliased Attribute Tracking**
   - Create a model with at least one field that has a Pydantic alias.
   - Generate the ontology graph.
   - Verify that the property in the ontology graph uses the alias (not the original field name) as its identifier.

2. **Non-Aliased Attribute Tracking**
   - Create a model with a field that does not have an alias.
   - Generate the ontology graph.
   - Verify that the property uses the field name as its identifier.

3. **Duplicate Alias Detection**
   - Create a model (or inheritance chain) where two fields resolve to the same alias (or field name if no alias).
   - Generate the ontology graph.
   - Confirm that a warning is emitted indicating that the property is defined multiple times and later definitions are ignored.

4. **Serialization Consistency**
   - Serialize an instance of the model.
   - Confirm that the serialized keys match the property identifiers in the ontology graph.

5. **RDF Parsing**
   - Parse the generated ontology graph with rdflib.
   - Confirm that aliased properties are correctly recognized and accessible.

Pydontology Team Architect
