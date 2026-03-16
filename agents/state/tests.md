- Write a test that defines an Entity with two fields sharing the same alias; verify that only the first is included in the ontology graph and a warning is emitted.
- Write a test that defines an Entity with both aliased and non-aliased fields; verify that the ontology graph uses the alias for aliased fields and the field name for others.
- Write a test that parses the ontology graph with rdflib and confirms that aliased properties are present as expected.
- Write a test that verifies a warning is emitted when duplicate property names (by alias or name) are detected.

— Pydontology Team Architect
