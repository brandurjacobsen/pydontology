import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    BaseContext,
    BaseMetaData,
    OntologyClass,
    OntologyProperty,
    Relation,
    Restriction,
)

CLASS_TYPE = "Ontology Class"
PROPERTY_TYPE = "Ontology Property"
CLASS_DIR = "classes"
PROPERTY_DIR = "properties"

CONVENTIONS_NOTE = (
    "RDF predicates are global: any property may be used with any subject. "
    "A class's `# Properties` section lists the properties declared on that "
    "class in the source model, and a property's `# Defined in` section lists "
    "the classes that declare it; neither is an exhaustive or restrictive list."
)

_ABSOLUTE_IRI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")


def _slugify(value: str) -> str:
    """Reduce an ontology id to a filesystem- and link-safe slug.

    Every run of characters outside ``[A-Za-z0-9]`` is collapsed to a single
    hyphen; leading and trailing hyphens are stripped. Case is preserved so the
    mapping stays recognizable.

    Args:
        value (str): Raw ontology id or label.

    Returns:
        str: The non-empty slug.

    Raises:
        ValueError: If the value has no alphanumeric characters at all.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    if not slug:
        raise ValueError(f"Cannot derive a filename slug from {value!r}")
    return slug


def _frontmatter_block(frontmatter: Mapping[str, str]) -> str:
    """Render an ordered frontmatter mapping as a YAML block.

    Values are emitted with ``json.dumps`` so that special characters are
    escaped; JSON string quoting is a valid YAML subset, which keeps the
    package free of a YAML dependency.

    Args:
        frontmatter (Mapping[str, str]): Ordered keys and string values.

    Returns:
        str: The ``---`` delimited block, or an empty string when the mapping
            is empty.
    """
    if not frontmatter:
        return ""
    lines = [f"{key}: {json.dumps(value)}" for key, value in frontmatter.items()]
    return "---\n" + "\n".join(lines) + "\n---\n\n"


def _slug_paths(ids: Sequence[str], directory: str) -> dict[str, str]:
    """Map ontology ids to bundle-relative concept paths.

    Args:
        ids (Sequence[str]): Ontology ids for one concept group.
        directory (str): Group directory, e.g. ``classes``.

    Returns:
        dict[str, str]: Mapping of id to ``<directory>/<slug>.md``.

    Raises:
        ValueError: If two ids in the group collapse to the same slug.
    """
    paths: dict[str, str] = {}
    seen: dict[str, str] = {}
    for ontology_id in ids:
        slug = _slugify(ontology_id)
        if slug in seen:
            raise ValueError(
                f"Concept filename collision in '{directory}': "
                f"{seen[slug]!r} and {ontology_id!r} both map to {slug!r}"
            )
        seen[slug] = ontology_id
        paths[ontology_id] = f"{directory}/{slug}.md"
    return paths


def _entry_id(entry: Relation | Restriction) -> str:
    """Reduce a subClassOf entry to its IRI string.

    Args:
        entry (Relation | Restriction): A relation or OWL restriction.

    Returns:
        str: The entry id, or ``owl:Restriction`` when a restriction is
            anonymous.
    """
    if isinstance(entry, Relation):
        return entry.id
    return entry.id or "owl:Restriction"


def _one_line(text: str | None) -> str | None:
    """Collapse a possibly multi-line comment into a single line.

    Args:
        text (str | None): Raw comment or docstring.

    Returns:
        str | None: Whitespace-normalized text, or None when empty.
    """
    if not text:
        return None
    return " ".join(text.split())


def _build_prefixes(context: BaseContext) -> dict[str, str]:
    """Derive the ordered prefix map used for compact IRIs.

    The vocabulary (``@vocab``, falling back to ``@base``) is exposed as the
    ``ex`` prefix so that bare local names can be written as compact IRIs.
    Arbitrary ``BaseContext`` extras are intentionally not treated as prefixes;
    only ``ex`` and the fixed ``owl``/``xsd``/``rdfs``/``sh`` namespaces are
    emitted.

    Args:
        context (BaseContext): The JSON-LD context supplying the namespaces.

    Returns:
        dict[str, str]: Prefix name to namespace IRI, ``ex`` first (when set).
    """
    prefixes: dict[str, str] = {}
    namespace = context.vocab or context.base
    if namespace:
        prefixes["ex"] = namespace
    prefixes["owl"] = str(context.owl)
    prefixes["xsd"] = str(context.xsd)
    prefixes["rdfs"] = str(context.rdfs)
    prefixes["sh"] = str(context.sh)
    return prefixes


def _resolve_term(iri: str, prefixes: Mapping[str, str]) -> tuple[str, bool]:
    """Render a concept id or IRI as a compact IRI when possible.

    Args:
        iri (str): The concept id or IRI.
        prefixes (Mapping[str, str]): Prefix name to namespace IRI.

    Returns:
        tuple[str, bool]: The rendered text and whether it resolved to an IRI
            (a known-prefix CURIE, an absolute IRI, or a bare name compacted
            through ``ex``). Unresolved bare names return ``(iri, False)``.
    """
    prefix, sep, local = iri.partition(":")
    if sep and prefix in prefixes and not local.startswith("//"):
        return iri, True
    for name, namespace in prefixes.items():
        if namespace and iri.startswith(namespace):
            return f"{name}:{iri[len(namespace) :]}", True
    if "ex" in prefixes and not _ABSOLUTE_IRI_RE.match(iri):
        return f"ex:{iri}", True
    return iri, bool(_ABSOLUTE_IRI_RE.match(iri))


def _iri_label(iri: str, prefixes: Mapping[str, str]) -> str:
    """Label an ontology term as an IRI or an unresolved relative name.

    Args:
        iri (str): The concept id or IRI.
        prefixes (Mapping[str, str]): Prefix name to namespace IRI.

    Returns:
        str: ``"IRI"`` when the term resolves to a compact or absolute IRI,
            otherwise ``"Relative IRI"``.
    """
    return "IRI" if _resolve_term(iri, prefixes)[1] else "Relative IRI"


@dataclass(frozen=True)
class _Layout:
    """Precomputed paths, titles, and membership for a bundle build.

    Attributes:
        class_paths (Mapping[str, str]): Class id to bundle-relative path.
        property_paths (Mapping[str, str]): Property id to bundle-relative path.
        class_titles (Mapping[str, str]): Class id to display title.
        property_titles (Mapping[str, str]): Property id to display title.
        class_members (Mapping[str, tuple[str, ...]]): Class id to ids of the
            properties it defines.
        property_members (Mapping[str, tuple[str, ...]]): Property id to the
            classes that define it.
        prefixes (Mapping[str, str]): Prefix name to namespace IRI.
    """

    class_paths: Mapping[str, str]
    property_paths: Mapping[str, str]
    class_titles: Mapping[str, str]
    property_titles: Mapping[str, str]
    class_members: Mapping[str, tuple[str, ...]]
    property_members: Mapping[str, tuple[str, ...]]
    prefixes: Mapping[str, str]

    @classmethod
    def build(
        cls,
        classes: Sequence[OntologyClass],
        properties: Sequence[OntologyProperty],
        defined_in: Mapping[str, Sequence[str]],
        prefixes: Mapping[str, str],
    ) -> "_Layout":
        """Derive a layout from the ontology registries.

        Args:
            classes (Sequence[OntologyClass]): Ontology classes.
            properties (Sequence[OntologyProperty]): Ontology properties.
            defined_in (Mapping[str, Sequence[str]]): Property id to the class
                ids that define it.
            prefixes (Mapping[str, str]): Prefix name to namespace IRI.

        Returns:
            _Layout: The precomputed layout.
        """
        class_paths = _slug_paths([c.id for c in classes], CLASS_DIR)
        property_paths = _slug_paths([p.id for p in properties], PROPERTY_DIR)

        class_members: dict[str, list[str]] = {}
        for prop in properties:
            for class_id in defined_in.get(prop.id, ()):
                class_members.setdefault(class_id, []).append(prop.id)

        return cls(
            class_paths=class_paths,
            property_paths=property_paths,
            class_titles={c.id: c.label or c.id for c in classes},
            property_titles={p.id: p.label or p.id for p in properties},
            class_members={cid: tuple(pids) for cid, pids in class_members.items()},
            property_members={
                p.id: tuple(defined_in.get(p.id, ())) for p in properties
            },
            prefixes=prefixes,
        )

    def class_link(self, class_id: str) -> str | None:
        """Return the POSIX markdown link target for a class.

        Args:
            class_id (str): Ontology class id.

        Returns:
            str | None: The bundle-relative link (``/classes/<slug>.md``), or
                None when the class is not part of the bundle.
        """
        path = self.class_paths.get(class_id)
        return f"/{path}" if path else None

    def property_link(self, property_id: str) -> str | None:
        """Return the POSIX markdown link target for a property.

        Args:
            property_id (str): Ontology property id.

        Returns:
            str | None: The bundle-relative link
                (``/properties/<slug>.md``), or None when the property is not
                part of the bundle.
        """
        path = self.property_paths.get(property_id)
        return f"/{path}" if path else None

    def class_reference(self, class_id: str) -> str:
        """Render a class id as a link when bundled, else as a compact IRI.

        Args:
            class_id (str): Ontology class id.

        Returns:
            str: A markdown link to the class concept, or the compact/verbatim
                IRI when the class is not part of the bundle.
        """
        link = self.class_link(class_id)
        if link is None:
            return _resolve_term(class_id, self.prefixes)[0]
        return f"[{self.class_titles.get(class_id, class_id)}]({link})"

    def property_reference(self, property_id: str) -> str:
        """Render a property id as a link when bundled, else a compact IRI.

        Args:
            property_id (str): Ontology property id.

        Returns:
            str: A markdown link to the property concept, or the
                compact/verbatim IRI when the property is not in the bundle.
        """
        link = self.property_link(property_id)
        if link is None:
            return _resolve_term(property_id, self.prefixes)[0]
        return f"[{self.property_titles.get(property_id, property_id)}]({link})"


class OKFDocument(BaseModel):
    """A single OKF document, either an ``index.md`` or a concept file.

    Attributes:
        path (str): Bundle-relative POSIX path, e.g. ``classes/Person.md``.
        frontmatter (dict[str, str]): Ordered frontmatter keys and string values.
        body (str): Markdown body rendered after the frontmatter.
    """

    path: str
    frontmatter: dict[str, str] = Field(default_factory=dict)
    body: str = ""

    def render(self) -> str:
        """Render this document to its full markdown text.

        Returns:
            str: The frontmatter block (if any) followed by the stripped body
                and a single trailing newline.
        """
        return _frontmatter_block(self.frontmatter) + self.body.strip() + "\n"

    model_config = ConfigDict(frozen=True)


class OKFBundle(BaseModel):
    """An in-memory Open Knowledge Format bundle.

    Attributes:
        name (str): Bundle directory name, e.g. the slugified ontology label.
        documents (list[OKFDocument]): The files that make up the bundle.
    """

    name: str
    documents: list[OKFDocument] = Field(default_factory=list)

    def render(self) -> dict[str, str]:
        """Render every document in the bundle.

        Returns:
            dict[str, str]: Mapping of bundle-relative path to markdown text.
        """
        return {document.path: document.render() for document in self.documents}

    def write(self, parent: str | PathLike) -> Path:
        """Write the bundle under ``parent/<name>``.

        Parent directories are created as needed and existing files are
        overwritten; unrelated files are left untouched.

        Args:
            parent (str | PathLike): Directory in which to create the bundle
                root.

        Returns:
            Path: The created bundle root directory, ``parent/<name>``.
        """
        root = Path(parent) / self.name
        root.mkdir(parents=True, exist_ok=True)
        for path, text in self.render().items():
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text, encoding="utf-8")
        return root

    model_config = ConfigDict(frozen=True)


def _entry_line(
    name: str,
    entries: Sequence[Relation | Restriction],
    reference: Callable[[str], str],
) -> str | None:
    """Render a comma-joined body line for a list of relation entries.

    Args:
        name (str): Line label without the trailing colon, e.g. ``Subclass of``.
        entries (Sequence[Relation | Restriction]): Entries to render.
        reference (Callable[[str], str]): Renders one entry id as a link or
            compact IRI.

    Returns:
        str | None: The rendered line, or None when there are no entries.
    """
    if not entries:
        return None
    return f"{name}: " + ", ".join(reference(_entry_id(entry)) for entry in entries)


def _class_document(cls: OntologyClass, layout: _Layout) -> OKFDocument:
    """Build the OKF concept document for an ontology class.

    Args:
        cls (OntologyClass): The class to serialize.
        layout (_Layout): Precomputed path and title lookups.

    Returns:
        OKFDocument: The class concept document.
    """
    blocks: list[str] = []
    if cls.comment:
        blocks.append(cls.comment)
    blocks.append(
        f"{_iri_label(cls.id, layout.prefixes)}: "
        f"{_resolve_term(cls.id, layout.prefixes)[0]}"
    )
    for line in (
        _entry_line("Subclass of", cls.subClassOf or [], layout.class_reference),
        _entry_line("Equivalent to", cls.equivalentClass or [], layout.class_reference),
    ):
        if line:
            blocks.append(line)

    members = layout.class_members.get(cls.id, ())
    if members:
        bullets = []
        for property_id in members:
            title = layout.property_titles.get(property_id, property_id)
            link = layout.property_link(property_id)
            bullets.append(f"* [{title}]({link})" if link else f"* {title}")
        blocks.append("# Properties\n\n" + "\n".join(bullets))

    return OKFDocument(
        path=layout.class_paths[cls.id],
        frontmatter={
            "type": CLASS_TYPE,
            "title": cls.label or cls.id,
            "resource": _resolve_term(cls.id, layout.prefixes)[0],
        },
        body="\n\n".join(blocks),
    )


def _property_document(prop: OntologyProperty, layout: _Layout) -> OKFDocument:
    """Build the OKF concept document for an ontology property.

    Args:
        prop (OntologyProperty): The property to serialize.
        layout (_Layout): Precomputed path and title lookups.

    Returns:
        OKFDocument: The property concept document.
    """
    blocks: list[str] = []
    if prop.comment:
        blocks.append(prop.comment)

    blocks.append(
        f"{_iri_label(prop.id, layout.prefixes)}: "
        f"{_resolve_term(prop.id, layout.prefixes)[0]}"
    )
    blocks.append(f"Type: {', '.join(prop.type)}")
    if prop.domain is not None:
        blocks.append(f"RDFS domain: {layout.class_reference(prop.domain.id)}")
    if prop.range is not None:
        blocks.append(f"RDFS range: {layout.class_reference(prop.range.id)}")
    if prop.subPropertyOf is not None:
        blocks.append(
            f"Subproperty of: {layout.property_reference(prop.subPropertyOf.id)}"
        )
    if prop.equivalentProperty is not None:
        blocks.append(
            f"Equivalent to: {layout.property_reference(prop.equivalentProperty.id)}"
        )
    if prop.inverseOf is not None:
        blocks.append(f"Inverse of: {layout.property_reference(prop.inverseOf.id)}")

    members = layout.property_members.get(prop.id, ())
    if members:
        bullets = []
        for class_id in members:
            title = layout.class_titles.get(class_id, class_id)
            link = layout.class_link(class_id)
            bullets.append(f"* [{title}]({link})" if link else f"* {title}")
        blocks.append("# Defined in\n\n" + "\n".join(bullets))

    return OKFDocument(
        path=layout.property_paths[prop.id],
        frontmatter={
            "type": PROPERTY_TYPE,
            "title": prop.label or prop.id,
            "resource": _resolve_term(prop.id, layout.prefixes)[0],
        },
        body="\n\n".join(blocks),
    )


def _list_section(
    heading: str,
    items: Sequence[OntologyClass | OntologyProperty],
    link_for: Callable[[str], str | None],
) -> str:
    """Render a markdown section of concept links for the index.

    Args:
        heading (str): Section heading, without the leading ``#``.
        items (Sequence[OntologyClass | OntologyProperty]): Concepts to list.
        link_for (Callable[[str], str | None]): Maps a concept id to its
            bundle-relative link.

    Returns:
        str: The heading followed by one bullet per concept, each optionally
            annotated with the concept's one-line comment.
    """
    lines = []
    for item in items:
        title = item.label or item.id
        link = link_for(item.id)
        line = f"* [{title}]({link})" if link else f"* {title}"
        description = _one_line(item.comment)
        if description:
            line += f" - {description}"
        lines.append(line)
    return f"# {heading}\n\n" + "\n".join(lines)


def _prefix_section(prefixes: Mapping[str, str]) -> str:
    """Render the copy-pasteable ``PREFIX`` block for the index.

    Args:
        prefixes (Mapping[str, str]): Prefix name to namespace IRI.

    Returns:
        str: A ``# Prefixes`` heading followed by a fenced ``sparql`` block with
            one ``PREFIX <name>: <namespace>`` line per entry.
    """
    lines = [f"PREFIX {name}: <{namespace}>" for name, namespace in prefixes.items()]
    return "# Prefixes\n\n```sparql\n" + "\n".join(lines) + "\n```"


def _index_document(
    metadata: BaseMetaData,
    classes: Sequence[OntologyClass],
    properties: Sequence[OntologyProperty],
    layout: _Layout,
) -> OKFDocument:
    """Build the bundle-root ``index.md`` document.

    Args:
        metadata (BaseMetaData): Ontology metadata; its comment opens the body.
        classes (Sequence[OntologyClass]): Ontology classes to list.
        properties (Sequence[OntologyProperty]): Ontology properties to list.
        layout (_Layout): Precomputed path, title, and prefix lookups.

    Returns:
        OKFDocument: The index document, carrying only the ``okf_version``
            frontmatter key.
    """
    blocks: list[str] = []
    comment = _one_line(metadata.comment)
    if comment:
        blocks.append(comment)
    blocks.append(_prefix_section(layout.prefixes))
    blocks.append(CONVENTIONS_NOTE)
    if classes:
        blocks.append(_list_section("Classes", classes, layout.class_link))
    if properties:
        blocks.append(_list_section("Properties", properties, layout.property_link))

    return OKFDocument(
        path="index.md",
        frontmatter={"okf_version": "0.2"},
        body="\n\n".join(blocks),
    )


def build_okf_bundle(
    *,
    name: str,
    metadata: BaseMetaData,
    classes: Sequence[OntologyClass],
    properties: Sequence[OntologyProperty],
    defined_in: Mapping[str, Sequence[str]],
    context: BaseContext | None = None,
) -> OKFBundle:
    """Build an OKF v0.2 bundle from ontology registries.

    Args:
        name (str): Bundle directory name (typically ``metadata.label`` or
            ``metadata.id``); slugified so the result is filesystem-safe.
        metadata (BaseMetaData): Ontology metadata for the index comment.
        classes (Sequence[OntologyClass]): Ontology classes.
        properties (Sequence[OntologyProperty]): Ontology properties.
        defined_in (Mapping[str, Sequence[str]]): Property id to the class ids
            that define it.
        context (BaseContext | None): JSON-LD context supplying the namespaces
            for compact IRIs. Defaults to an empty ``BaseContext``.

    Returns:
        OKFBundle: The in-memory bundle, with the index first and all concept
            documents (and index entries) sorted by id.
    """
    prefixes = _build_prefixes(context if context is not None else BaseContext())
    ordered_classes = sorted(classes, key=lambda c: c.id)
    ordered_properties = sorted(properties, key=lambda p: p.id)
    layout = _Layout.build(ordered_classes, ordered_properties, defined_in, prefixes)
    documents = [_index_document(metadata, ordered_classes, ordered_properties, layout)]
    documents += [_class_document(cls, layout) for cls in ordered_classes]
    documents += [_property_document(prop, layout) for prop in ordered_properties]
    return OKFBundle(name=_slugify(name), documents=documents)
