Implement attribute tracking for ontology properties as follows:

- When a field in an Entity model has a Pydantic alias, use the alias as the property identifier in the ontology graph and in all serialized outputs. The original field name must not appear as a property identifier when an alias is present.
- When no alias is set, use the field name itself as the property identifier.
- If two fields (within a class or across an inheritance chain) resolve to the same property identifier (either by alias or field name), emit a warning and ensure only the first definition is used in the ontology graph. Later definitions must be ignored to avoid duplicate triples.
- Ensure that the keys in serialized model instances match the property identifiers used in the ontology graph.
- Aliased and non-aliased properties must be correctly accessible and typed in the generated RDF graph.

Pydontology Team Architect
