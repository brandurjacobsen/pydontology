- Update the `JSONLDGraph._create_property_definitions()` method:
  - Track properties by `field_info.alias` if present, otherwise by `field_name`.
  - Use `field_info.alias or field_name` as the key in the `properties_seen` set.
  - Import the `warnings` module and emit a warning if a duplicate property name (by alias or name) is detected, with the message: "Property '{name}' defined multiple times; later definitions ignored".
- Ensure that the `prop_name` parameter in `_create_single_property_definition()` reflects the alias-aware property name.
- No changes are required for SHACL graph generation.
- Maintain backward compatibility for fields without aliases.

— Pydontology Team Architect
