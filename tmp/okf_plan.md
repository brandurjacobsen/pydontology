# Implementation Plan: OKF v0.2 bundle from Pydontology

## Goal

Add the ability for a `Pydontology` instance to emit an
[Open Knowledge Format (OKF) v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format)
bundle describing the `ontology` union of `Entity` classes and the properties
derived from their fields.

The bundle is a directory named after `metadata.label` (falling back to
`metadata.id`), containing an `index.md` and one concept file per class and per
property.

## Decisions locked in (from design interview)

| Topic | Decision |
|-------|----------|
| API shape | In-memory `OKFBundle` model + `OKFBundle.write(parent)` for disk output |
| Entry point | `Pydontology.okf_bundle(settings=Settings()) -> OKFBundle` |
| Module | New `pydontology/okf.py` |
| Missing metadata | Raise a clear `ValueError` at the `Pydontology` boundary |
| Root name | `metadata.label` else `metadata.id`; slugified |
| Layout | `<root>/index.md`, `<root>/classes/<Class>.md`, `<root>/properties/<prop>.md` |
| Naming | Slugify non-alphanumerics to `-`, keep case; raise on collisions |
| Concept types | `"Ontology Class"` / `"Ontology Property"` |
| Root frontmatter | `okf_version: "0.2"` (only permitted index frontmatter) |
| Class body | docstring, IRI line, "Subclass of", `# Properties` links (own-defined only) |
| Property body | field description, `# Defined in` links |
| Frontmatter | Hand-serialized YAML; JSON-quoted string scalars (`json.dumps`), no PyYAML |
| `resource` | Ontology id verbatim (e.g. `Person`, `knows`) |
| `title` | `rdfs:label` if set, else id |
| Parent rendering | Markdown link when parent is a generated class; otherwise plain text (`owl:Thing`, restrictions) |
| Settings | Accept `settings`, rebuild registries, honor label/comment/subclass toggles |
| `write` semantics | `mkdir(parents=True, exist_ok=True)`, overwrite files, never delete |
| Verification | Unit tests + docs + package exports |

---

## Simplification pass (changes from the first draft)

The first draft had three document shapes and special-cased the index file.
The leaner design below removes that branching and the parameter sprawl.

1. **One generic document type.** `OKFDocument` is `path` (bundle-relative,
   POSIX) + `frontmatter` (an ordered `dict[str, str]`) + `body`. Frontmatter
   keys are supplied by the builders, so `type`/`title`/`resource`/`extra`
   become data, not fields.
2. **The index is an ordinary document.** It is just an `OKFDocument` with
   `path="index.md"` and `frontmatter={"okf_version": "0.2"}` and no `type`.
   This deletes the `index` field, the `extra` field, and the `is_index` /
   `frontmatter_only_extras` flag. `OKFDocument.render()` has no special case.
3. **`OKFBundle` holds a flat list.** `name` + `documents: list[OKFDocument]`.
   No `index` vs `concepts` split; `render()` is a dict comprehension.
4. **A `_Layout` parameter object.** Path maps, title maps, and class↔property
   membership are computed once and passed as one frozen value object, replacing
   the parallel `class_ids` / `property_paths` / `subclass_targets` arguments
   scattered across the builders.
5. **Membership comes from the registry, not from `domain`.** Class→property
   and property→class edges use `_prop_db[id]["defined_in"]`, which is correct
   even when `ORIGIN_AS_DOMAIN` suppresses `rdfs:domain` for multi-class
   properties.
6. **No `tools.py` import.** `okf.py` must not import `pydontology.tools`: that
   module imports `jinja2` at import time and raises when the optional extra is
   absent. A tiny local `_entry_id` helper handles `Relation`/`Restriction`.

## Best practices to hold

- **Pure functions, single responsibility.** `okf.py` builds data; only
  `OKFBundle.write` touches the filesystem. `Pydontology.okf_bundle` is a thin
  adapter (validate, apply settings, delegate).
- **No boolean flag arguments** and no mode switches; the generic document shape
  makes branching unnecessary.
- **Validate at the boundary.** `metadata is None` is rejected in
  `okf_bundle()`; `build_okf_bundle` receives a non-optional `BaseMetaData` and
  stays total.
- **Portable links.** Bundle-relative links are always POSIX (`/classes/X.md`),
  built with string formatting — never `os.path.join`, which would emit
  backslashes on Windows. `pathlib` is used only for disk I/O.
- **Deterministic output.** Documents are emitted sorted by id (index first) so
  bundles are stable and diffable.
- **Dependency-free frontmatter.** Ordered `key: <json.dumps(value)>` lines are
  a valid YAML subset; no PyYAML.
- **Consistency with the package.** `OKFDocument`/`OKFBundle` are Pydantic
  models exported from `__init__`, matching `JSONLDGraph` et al. `_Layout` is a
  frozen dataclass.
- **Repo code style.** No comments in implementation code (docstrings only, on
  public objects/functions).
- **Google-style docstrings.** Every function, method, and class gets a
  Google-style docstring (summary line, then `Args:` / `Returns:` / `Raises:`
  / `Attributes:` sections as applicable), matching the style already used in
  `rdfs.py`. This applies to `_slugify`, `_frontmatter_block`, `_Layout` and
  its methods, every builder, and both Pydantic models.
- **Focused tests.** A small purpose-built ontology drives the unit tests; one
  integration test uses `TestModel`; disk writes use `tmp_path`.

---

## Phase 1 — Document model, rendering, and helpers (`pydontology/okf.py`)

**Deliverable:** the module exists with the value models and pure helpers, with
no `Pydontology` wiring yet.

1. Create `pydontology/okf.py`.
2. `_slugify(value: str) -> str`:
   - `re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")`.
   - Raise `ValueError` if the result is empty.
3. Frontmatter rendering:
   - `_frontmatter_block(frontmatter: Mapping[str, str]) -> str`:
     - empty mapping -> `""`;
     - otherwise `---\n` + `key: json.dumps(value)` lines + `\n---\n\n`.
   - Values are always strings, so `json.dumps` yields valid YAML scalars;
     `okf_version: "0.2"` comes out exactly as the spec shows.
4. `OKFDocument(BaseModel)` with `model_config = ConfigDict(frozen=True)`:
   - `path: str` (bundle-relative, POSIX, e.g. `classes/Person.md`).
   - `frontmatter: dict[str, str]` (insertion-ordered).
   - `body: str`.
   - `render() -> str` = `_frontmatter_block(frontmatter) + body.strip() + "\n"`.
5. `OKFBundle(BaseModel)` with `model_config = ConfigDict(frozen=True)`:
   - `name: str`.
   - `documents: list[OKFDocument]`.
   - `render() -> dict[str, str]` = `{d.path: d.render() for d in documents}`.
   - `write(parent: str | PathLike) -> Path`:
     - `root = Path(parent) / self.name`;
     - for each `path, text` in `render()`: `dest = root / path`,
       `dest.parent.mkdir(parents=True, exist_ok=True)`,
       `dest.write_text(text, encoding="utf-8")`;
     - return `root`.
6. Tests can construct documents directly; no disk needed.

**Exit criteria:** module imports cleanly; a hand-built `OKFBundle` renders the
expected markdown and writes the expected tree to a temp dir.

---

## Phase 2 — Layout and builders

**Deliverable:** pure functions turning the registries into an `OKFBundle`.

1. `_Layout` (frozen dataclass), built once by
   `_Layout.build(classes, properties, defined_in)`:
   - `class_paths: Mapping[str, str]` — id -> `classes/<slug>.md`.
   - `property_paths: Mapping[str, str]` — id -> `properties/<slug>.md`.
   - `class_titles: Mapping[str, str]` and `property_titles` — `label or id`.
   - `class_members: Mapping[str, tuple[str, ...]]` — class id -> own prop ids.
   - `property_members: Mapping[str, tuple[str, ...]]` — `defined_in` verbatim.
   - `class_link(id) -> str | None` / `property_link(id) -> str | None`:
     return `"/" + path` when present, else `None` (POSIX links).
   - `_Layout.build` slugifies every id and raises `ValueError` listing any
     ids that collapse to the same slug (checked per group: classes and
     properties).
   - `_entry_id(entry) -> str`: `entry.id` for `Relation`;
     `entry.id or "owl:Restriction"` for `Restriction`.
2. `_class_document(cls, layout) -> OKFDocument`:
   - `path = layout.class_paths[cls.id]`,
     `frontmatter = {"type": "Ontology Class", "title": cls.label or cls.id,
     "resource": cls.id}`.
   - Body parts:
     - `cls.comment` if present (this is the docstring by default).
     - `IRI: <cls.id>`.
     - `Subclass of:` join over `cls.subClassOf`:
       `[id](/classes/<slug>.md)` when `layout.class_link(id)` is set, else the
       plain id (`owl:Thing`, `owl:Restriction`, external IRIs); omit the line
       when `subClassOf` is empty.
     - `# Properties` + `* [<title>](/properties/<slug>.md)` for each id in
       `layout.class_members.get(cls.id, ())`; omit when empty.
3. `_property_document(prop, layout) -> OKFDocument`:
   - `path = layout.property_paths[prop.id]`,
     `frontmatter = {"type": "Ontology Property", "title": prop.label or prop.id,
     "resource": prop.id}`.
   - Body: `prop.comment` if present; then `# Defined in` +
     `* [<title>](/classes/<slug>.md)` for each id in
     `layout.property_members.get(prop.id, ())`; omit when empty.
4. `_index_document(metadata, classes, properties, layout) -> OKFDocument`:
   - `path = "index.md"`, `frontmatter = {"okf_version": "0.2"}` (no `type`).
   - Body: `metadata.comment` first; then `# Classes` and `# Properties`
     sections of `* [<title>](/<group>/<slug>.md) - <description>` where the
     description is `cls.comment` / `prop.comment` (the ` - desc` suffix is
     omitted when there is no comment).
5. `build_okf_bundle(*, name, metadata, classes, properties, defined_in) -> OKFBundle`:
   - `layout = _Layout.build(classes, properties, defined_in)`.
   - `documents = [_index_document(...)] + sorted class docs + sorted property
     docs` (sorted by id).
   - Return `OKFBundle(name=name, documents=documents)`.

**Exit criteria:** `build_okf_bundle` produces a bundle whose `render()` matches
hand-written expectations for a small ontology, including link/parent forms.

---

## Phase 3 — `Pydontology` wiring and exports

**Deliverable:** the public API.

1. `pydontology/pydontology.py`:
   - Import `build_okf_bundle` and `OKFBundle` from `.okf`.
   - Add:
     ```python
     def okf_bundle(self, settings: Settings = Settings()) -> OKFBundle:
         if self.metadata is None:
             raise ValueError(
                 "metadata is required to generate an OKF bundle "
                 "(used for the bundle root name and index comment)"
             )
         self._apply_settings(settings)
         return build_okf_bundle(
             name=self.metadata.label or self.metadata.id,
             metadata=self.metadata,
             classes=self._create_ontology_classes(),
             properties=self._create_ontology_properties(),
             defined_in={
                 pid: info["defined_in"] for pid, info in self._prop_db.items()
             },
         )
     ```
   - Reuse the existing private builders so Settings and annotations behave
     exactly as in `ontology_graph()`.
2. `pydontology/__init__.py`: export `OKFBundle` and `OKFDocument`, add both to
   `__all__`.

**Exit criteria:** `Pydontology(...).okf_bundle()` returns a bundle; calling it
without metadata raises `ValueError`; settings (labels/comments/subclass) are
honored.

---

## Phase 4 — Tests (`tests/test_okf.py`)

**Deliverable:** focused `pytest` coverage.

Cases:

1. **Root name**: `name` is `metadata.label` when set, `metadata.id` otherwise.
2. **Missing metadata**: `okf_bundle()` raises `ValueError`.
3. **Index**: `okf_version: "0.2"` frontmatter, metadata comment first,
   `# Classes` / `# Properties` bullets with `/classes/...md` and
   `/properties/...md` links and descriptions.
4. **Class document**: docstring-first body, `IRI:` line, parent as a link for
   a generated parent and plain `owl:Thing` otherwise, own-defined properties
   only.
5. **Property document**: field description and `# Defined in` links to every
   defining class (e.g. `company` -> Employee and Department).
6. **Determinism**: `render()` keys/values are identical across two calls.
7. **`write()`**: expected tree under `tmp_path`; a second write overwrites
   generated files and leaves unrelated files untouched.
8. **Slugging/collisions**: unsafe ids produce slugged filenames; a constructed
   collision raises `ValueError`.

A small local ontology drives cases 1–6 and 8; one `TestModel`-based test
covers integration. Disk assertions use `tmp_path`.

**Exit criteria:** `pytest tests/test_okf.py` passes; full `pytest` stays green.

---

## Phase 5 — Documentation

**Deliverable:** docs and agent notes reflect the feature.

1. `mkdocs/reference.md`: an "OKF bundle" section covering
   `Pydontology.okf_bundle()`, `OKFBundle.write()`, root naming, layout, and
   the document conventions.
2. `README.md`: mirror the section.
3. `AGENTS.md`: add `okf_bundle()` to "Key APIs" and note the metadata
   requirement and the `okf.py` module under extension points.

**Exit criteria:** docs render with no broken references; README and reference
agree.

---

## Phase 6 — Final verification

1. `pytest`.
2. `ruff check pydontology tests` and `ruff format --check`.
3. End-to-end write to a temp directory and eyeball the tree.
4. Confirm no new runtime dependency (frontmatter is hand-serialized).

**Exit criteria:** tests, lint, and format clean; every concept file carries a
`type` and the reserved `index.md` carries only `okf_version`, satisfying the
producer-side OKF v0.2 conformance rules.

---

## Out of scope (explicitly deferred)

- `log.md` update history.
- OKF trust/provenance/lifecycle families (`generated`, `verified`, `status`,
  `stale_after`, `sources`).
- Attested Computation concepts.
- Back-links from index to subdirectories (files are flat within each group).
- Wiping/cleaning the output directory on `write()`.
