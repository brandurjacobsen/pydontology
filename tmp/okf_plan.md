# OKF Bundle Refactoring Plan

## Goal

Replace the current OKF bundle generation with an architecture where:

1. `ontology_graph()` and `shacl_graph()` serialize to JSON-LD
2. rdflib parses the JSON-LD into graphs
3. rdflib queries populate view dataclasses imperatively
4. Jinja2 templates render view dataclasses into markdown documents

The rdflib representation (after prefix expansion) is the authoritative source.
All data flows through the graphs — no side-channel access to internal registries.

## Design decisions

| Decision | Choice |
|---|---|
| Authoritative source | rdflib graph after JSON-LD prefix expansion |
| Property-to-class membership | `rdfs:domain` always emitted; settings control when present |
| SHACL integration | Parsed primarily for `sh:closed`/`sh:ignoredProperties`; open for more |
| View dataclasses | Store `URIRef` objects; templates do assembly |
| URI compaction in templates | Jinja2 filters (`\|compact_iri`, `\|slugpath`) + graph as env global |
| Concept file paths | Pre-computed `path` string in each view (slug + collision at build time) |
| Dependencies | rdflib + jinja2 stay optional (`[tools]` extra); `ImportError` guards |
| Prefixes | Extracted from `graph.namespace_manager.namespaces()` — no synthetic `ex:` |
| Templates | New `.md.j2` files, matching current test-asserted markdown shape |
| Tests | Pure functions (`_slugify`) unit-tested; bundle path tested through `Pydontology` |
| okf_helpers.py | **Deleted** — remnants folded into `okf.py` |
| Old builders | `_Layout`, `_Member`, `_build_views`, `build_okf_bundle` — all removed |

---

## Phase 1: Create templates

**Goal:** The three Jinja2 templates exist and render correct markdown.

### 1.1 Write `pydontology/templates/class.md.j2`

- Frontmatter: `type`, `title`, `resource`
- Header: comment (if present)
- `IRI:` or `Relative IRI:` with compact/resolved term
- `Subclass of:` list (linked references to parent concepts)
- `Equivalent to:` list (linked references)
- `# Applicable properties` section: own properties first, then inherited (id-sorted within each group)
  - Own: `* [title](link)`
  - Inherited: `* [title](link) - inherited from [ancestor](link)`
- Closed-shape note when `sh:closed` is true

### 1.2 Write `pydontology/templates/property.md.j2`

- Frontmatter: `type`, `title`, `resource`
- Header: comment (if present)
- `IRI:` or `Relative IRI:` with compact/resolved term
- `Type:` comma-separated list of rdf:type values
- `RDFS domain:` linked reference (if present)
- `RDFS range:` linked reference (if present)
- `Subproperty of:` linked reference (if present)
- `Equivalent to:` reference (if present)
- `Inverse of:` reference (if present)
- `# Defined in` section: links to declaring classes

### 1.3 Write `pydontology/templates/index.md.j2`

- Frontmatter: `okf_version: "0.2"`
- Ontology comment (if present)
- `# Prefixes` section: `PREFIX name: <namespace>` block
- Conventions note
- `# Classes` section: `* [title](link) - comment` per class
- `# Properties` section: `* [title](link) - comment` per property

### 1.4 Tests

- Write new tests that verify rendered markdown against the same shape as current `test_okf.py` assertions
- Test with `TestModel` conftest fixture for integration coverage

---

## Phase 2: Build rdflib query module

**Goal:** `pydontology/okf_queries.py` exists and can extract all needed data from graphs.

### 2.1 Create `pydontology/okf_queries.py`

Module responsibilities:
- Parse JSON-LD strings into `rdflib.Dataset`
- Extract namespace bindings from `graph.namespace_manager`
- Query for classes, properties, SHACL shapes
- Compute membership (properties per class, classes per property) via `rdfs:subClassOf` + `rdfs:domain`
- Build `IndexView`, `ClassView`, `PropertyView` dataclasses

Internal structure:

```python
def query_ontology(
    onto_jsonld: str,
    shacl_jsonld: str | None,
) -> tuple[IndexView, list[ClassView], list[PropertyView]]:
    ...
```

Helper queries:
- `_extract_namespaces(graph) -> dict[str, str]` — from `namespace_manager.namespaces()`
- `_query_classes(graph) -> list[dict]` — all `rdfs:Class`/`owl:Class` subjects with labels, comments, subClassOf, equivalentClass
- `_query_properties(graph) -> list[dict]` — all property subjects with labels, comments, domains, ranges, subPropertyOf, equivalentProperty, inverseOf, types
- `_query_shacl(shacl_graph) -> dict[str, dict]` — NodeShapes keyed by targetClass, with closed, ignoredProperties, property shapes
- `_build_class_hierarchy(classes) -> dict[str, list[str]]` — parent→child and child→ancestors from `rdfs:subClassOf`
- `_build_membership(classes, properties) -> dict[str, list[Member]]` — per-class applicable properties with inheritance attribution
- `_build_views(...)` — assembles ClassView/PropertyView/IndexView

### 2.2 View dataclasses (in `okf.py`)

```python
@dataclass
class PrefixEntry:
    name: str       # "owl", "rdfs", etc.
    namespace: str  # "http://www.w3.org/2002/07/owl#"

@dataclass
class Reference:
    uriref: rdflib.URIRef | None   # None for owl:Thing / unresolvable
    title: str
    path: str | None               # bundle-relative link, None if external

@dataclass
class PropertyRef:
    uriref: rdflib.URIRef
    title: str
    path: str
    inherited_from: Reference | None

@dataclass
class ClassView:
    path: str
    frontmatter: dict[str, str]
    comment: str | None
    uriref: rdflib.URIRef
    sub_class_of: list[Reference]
    equivalent_class: list[Reference]
    properties: list[PropertyRef]
    closed: bool
    ignored_properties: list[str]

@dataclass
class PropertyView:
    path: str
    frontmatter: dict[str, str]
    comment: str | None
    uriref: rdflib.URIRef
    types: list[str]
    domain: Reference | None
    range: Reference | None
    sub_property_of: Reference | None
    equivalent_property: Reference | None
    inverse_of: Reference | None
    defined_in: list[Reference]

@dataclass
class IndexView:
    path: str  # "index.md"
    frontmatter: dict[str, str]
    comment: str | None
    prefixes: list[PrefixEntry]
    conventions_note: str
    classes: list[Reference]
    properties: list[Reference]
```

### 2.3 Tests

- Unit tests for `_slugify` (pure function, no rdflib needed)
- Unit tests for collision detection in path mapping
- Integration test: `Pydontology` → `ontology_graph()` + `shacl_graph()` → JSON-LD → `query_ontology()` → verify view contents

---

## Phase 3: Rewrite `okf.py` orchestration

### 3.1 Rewrite `build_okf_bundle` → `build_okf_bundle_from_graphs`

```python
def build_okf_bundle_from_graphs(
    *,
    name: str,
    metadata: BaseMetaData,
    onto_graph: JSONLDGraph,
    shacl_graph: JSONLDGraph | None = None,
    template_dir: str | PathLike | None = None,
) -> OKFBundle:
```

Steps:
1. Guard imports: `jinja2`, `rdflib`
2. Serialize `onto_graph.model_dump_json(exclude_none=True)`
3. Serialize `shacl_graph.model_dump_json(exclude_none=True)` (if present)
4. Call `query_ontology(onto_jsonld, shacl_jsonld)` → views
5. Set up Jinja2 environment with `PackageLoader` or `FileSystemLoader`
6. Register filters: `|compact_iri` (closure over namespace_manager), `|slugpath` (closure over path lookup), `|ref` (renders Reference as markdown link)
7. Inject namespace_manager / path_lookup as env globals
8. Render each view → `OKFDocument`
9. Return `OKFBundle(name=_slugify(name), documents=[...])`

### 3.2 Rewire `Pydontology.okf_bundle()`

```python
def okf_bundle(self, context=..., settings=..., template_dir=None):
    self._apply_settings(settings)
    onto = self.ontology_graph(context=context, settings=settings)
    shacl = self.shacl_graph(context=context, settings=settings)
    return build_okf_bundle_from_graphs(
        name=self.metadata.label or self.metadata.id,
        metadata=self.metadata,
        onto_graph=onto,
        shacl_graph=shacl,
        template_dir=template_dir,
    )
```

### 3.3 Remove old code

Delete from `okf.py`:
- `_build_views()`
- `_class_reference()`
- `_property_reference()`
- `build_okf_bundle()`

Delete `okf_helpers.py` entirely.

Keep in `okf.py`:
- `OKFDocument`, `OKFBundle` (unchanged)
- `CONVENTIONS_NOTE`
- `_slugify()`, `_one_line()`
- `_render_document()`
- View dataclasses (new shapes from Phase 2)
- Constants: `CLASS_TYPE`, `PROPERTY_TYPE`, `CLASS_DIR`, `PROPERTY_DIR`

### 3.4 Tests

- Rewrite `test_okf.py` to use `Pydontology` instances for all bundle tests
- Add tests for custom template_dir override
- Add tests for missing dependency guards (jinja2, rdflib)
- Verify rendered markdown matches existing assertion shape

---

## Phase 4: Cleanup

### 4.1 Update pyproject.toml

Add `rdflib` to `[project.optional-dependencies].tools`:
```
tools = ["jinja2", "rdflib"]
```

### 4.2 Update imports

- `pydontology/__init__.py`: update exports if needed
- `pydontology/pydontology.py`: update `build_okf_bundle` import → `build_okf_bundle_from_graphs`

### 4.3 Update documentation

- `AGENTS.md`: update OKF bundle section to describe new architecture
- `mkdocs/reference.md`: update if it references OKF internals

---

## File manifest

| File | Action |
|---|---|
| `pydontology/okf.py` | Rewrite: new view dataclasses, `build_okf_bundle_from_graphs()`, filters, merged helpers |
| `pydontology/okf_helpers.py` | **Delete** |
| `pydontology/okf_queries.py` | **Create**: all rdflib query logic |
| `pydontology/templates/index.md.j2` | **Create** |
| `pydontology/templates/class.md.j2` | **Create** |
| `pydontology/templates/property.md.j2` | **Create** |
| `pydontology/pydontology.py` | Edit: `okf_bundle()` now calls graphs + new builder |
| `pydontology/__init__.py` | Edit: maybe add `build_okf_bundle_from_graphs` to exports |
| `pyproject.toml` | Edit: add `rdflib` to `[tools]` |
| `tests/test_okf.py` | Rewrite: all tests through `Pydontology` |
| `AGENTS.md` | Edit: update OKF section |

---

## Migration notes

- The public API `Pydontology.okf_bundle(context, settings, template_dir)` is unchanged in signature and return type.
- `build_okf_bundle()` (low-level) is replaced by `build_okf_bundle_from_graphs()` with a different signature — this was not part of the public API.
- The rendered markdown output matches the current format exactly (same frontmatter keys, same sections, same link structure).
- Custom templates via `template_dir` continue to work with the new view dataclasses (template authors need to update to new field names).