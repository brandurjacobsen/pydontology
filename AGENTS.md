# AGENTS

## Project snapshot
- Pydontology builds RDF/OWL ontologies, SHACL shapes, and JSON schemas from Pydantic models.
- It uses `typing.Annotated` metadata to express RDFS/OWL/SHACL constructs.
- Core entry point: `Pydontology` in `pydontology/pydontology.py`.

## Core mental model
- Define ontology classes by subclassing `Entity` from `pydontology/models.py`.
- Use `Relation` for IRI-valued fields; other fields are treated as literals.
- Use `LangStr` for language-tagged literal fields (value + BCP47 tag from `pydontology/bcp47.py`); it is whitelisted alongside `Relation` under `TYPE_STRICT_MODE` and is exempt from TypeVal wrapping.
- Add annotations via `typing.Annotated` using `RDFSAnnotation`, `OWLAnnotation`, `SHACLAnnotation`.
- `Pydontology(ontology_union)` builds internal class/property registries.
- `ontology_graph()` emits a JSON-LD graph of classes and properties.
- `shacl_graph()` emits SHACL node/property shapes from annotations and defaults.
- `jsonld_graph()` (alias `schema_graph()`) builds a JSON-LD data graph model; its `model_json_schema()` is the JSON schema.

## Key APIs (use these first)
- `Entity`: base class for ontology classes; provides `@id` and `@type`.
- `Relation`: IRI wrapper for object properties.
- `LangStr`: language-tagged literal wrapper (value + BCP47 language tag).
- `Pydontology`: orchestrates graph generation.
- `Settings`: controls default behaviors (labels, comments, domains, types, warnings).
- `ontology_graph()`, `shacl_graph()`, `jsonld_graph()` (alias `schema_graph()`) on `Pydontology`.

## Defaults and behaviors (Settings)
- Class label/comment: class name and docstring by default.
- Property label/comment: field name and description by default.
- Domain: origin class by default unless property defined in multiple classes.
- Subclassing: parent class or `owl:Thing` default when inheriting from `Entity`.
- Type strictness: field types must resolve to a concrete type, `Relation`, or `LangStr`.
- LangStr fields yield `owl:DatatypeProperty` with no `xsd:*` rdf:type and no default SHACL property shape (language-tagged literals carry are implicitly xsd:string).
- Type map: Python types map to `xsd:*` (see `TYPE_MAP` in `pydontology/pydontology.py`).

## Supported constructs
- RDFS: `subClassOf`, `subPropertyOf`, `domain`, `range`, `comment`, `label`, `seeAlso`, `isDefinedBy`.
- OWL: `equivalentClass`, `equivalentProperty`, `inverseOf`, property characteristics (symmetric, transitive, functional, inverse functional), `intersectionOf`.
- SHACL: datatype, nodeKind, class, cardinality, numeric ranges, string constraints, property pair constraints, severity, name/description.
- See `mkdocs/reference.md` for the current supported list.

## Known limitations and footguns
- Multiple inheritance on class definitions is not supported; use annotations after definition.
- SHACL `sh:in` exists in annotation types but is not wired into graph output.
- Properties defined in multiple classes suppress default domain/comment and emit warnings (if enabled).
- Strict type checking can raise errors when a field type is not in the type map.

## Extension points
- Add new OWL/RDFS/SHACL constructs by extending annotation dataclasses in:
  - `pydontology/owl.py`, `pydontology/rdfs.py`, `pydontology/shacl.py`
- Wire new annotations into graph output in `pydontology/pydontology.py`:
  - `_add_class_annotations`, `_add_property_annotations`, `_add_shacl_annotations`.
- Add validators in `pydontology/validators.py` and reference via `AfterValidator`.
- Extend `TYPE_MAP` in `pydontology/pydontology.py` and update tests if needed.

## Tests and dependencies
- Tests live in `tests/` and use `pytest`.
- Graph validation uses `rdflib` and `pyshacl` (see optional deps in `pyproject.toml`).
- Run: `pytest` (ensure optional test deps installed).

## Docs and releases
- MkDocs sources in `mkdocs/`, config in `mkdocs.yml`, output in `docs/`.
- README mirrors mkdocs index content.
- Distribution is currently via TestPyPI; version is in `pyproject.toml`.
