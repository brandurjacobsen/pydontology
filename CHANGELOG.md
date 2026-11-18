# Changelog

## 2026.11.18

### Added
- **`sh:in` constraint** — fully functional via `SHACLAnnotation.shIn([...])`, serializes as proper RDF list.
- **`py.typed` marker** — PEP 561 compliance for `mypy`/`pyright` type-checking.
- **`LangStr` model** — language-tagged RDF literals with BCP47 tag validation.
- **`sh:languageIn` constraint** — restricts allowed language tags for `LangStr` fields.
- **OKF v0.2 bundle support** — `okf_bundle()` generates markdown-with-YAML concept documents from ontology and SHACL graphs.
- **IRI rewriting** — normalize `@id` values on serialization via `IRI_REWRITER` context key; subclasses can opt out.
- Full test coverage for all RDFS, OWL, and SHACL constructs (160 tests).

### Fixed
- `sh:ignoredProperties` now serializes as a proper RDF list (`{"@list": [...]}`) instead of a plain JSON array.
- `sh:in` annotation wired into graph output (was defined but disconnected).
- OKF index `PREFIX` block now uses fenced SPARQL format.
- `SHACLAnnotation.severity()` docstring return type corrected.
- Stale commented-out code, dead comments, and unused definitions removed.
- `AGENTS.md` updated to reflect current state of all constructs and test policy.
- Docs CI: `mkdocs-darkly` → `mkdocs-bootswatch`, `docstring_style` moved into `options` for mkdocstrings-python v2.x.
- `OntologyClass`/`OntologyProperty` renamed from private `_`-prefixed names to public.

### Changed
- **Development status**: Beta → Production/Stable.
- **Version scheme**: semantic (`1.1.0`) → calendar (`2026.11.18`).
- `BaseContext` no longer emits a default `@vocab` or `@base`, leaving IRIs relative by default.
