from collections.abc import Mapping, Sequence
from os import PathLike
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    BaseContext,
    BaseMetaData,
    OntologyClass,
    OntologyProperty,
)
from .okf_helpers import (
    CLASS_TYPE,
    CONVENTIONS_NOTE,
    PROPERTY_TYPE,
    _build_prefixes,
    _entry_line,
    _frontmatter_block,
    _iri_label,
    _Layout,
    _list_section,
    _one_line,
    _prefix_section,
    _resolve_term,
    _slugify,
)


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


def _applicable_block(cls: OntologyClass, layout: _Layout) -> str | None:
    """Render the ``# Applicable properties`` section for a class.

    Own-declared properties come first; inherited ones follow, each marked
    with the nearest declaring ancestor. A close-shape note is added when the
    class's node shape is closed.

    Args:
        cls (OntologyClass): The class to render.
        layout (_Layout): Precomputed membership and shape lookups.

    Returns:
        str | None: The rendered section, or None when the class has no
            applicable properties and no closed-shape marker.
    """
    members = layout.class_members.get(cls.id, ())
    ignored = layout.closed.get(cls.id)
    if not members and ignored is None:
        return None

    paragraphs: list[str] = []
    if ignored is not None:
        note = "Closed shape (`sh:closed`): only these properties are allowed"
        if ignored:
            note += " (plus ignored: " + ", ".join(ignored) + ")"
        paragraphs.append(note + ".")

    if members:
        bullets = []
        for member in members:
            title = layout.property_titles.get(member.property_id, member.property_id)
            link = layout.property_link(member.property_id)
            bullet = f"* [{title}]({link})" if link else f"* {title}"
            if member.inherited_from is not None:
                bullet += (
                    f" - inherited from {layout.class_reference(member.inherited_from)}"
                )
            bullets.append(bullet)
        paragraphs.append("\n".join(bullets))

    return "# Applicable properties\n\n" + "\n\n".join(paragraphs)


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

    applicable = _applicable_block(cls, layout)
    if applicable:
        blocks.append(applicable)

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
    closed: Mapping[str, Sequence[str]] | None = None,
) -> OKFBundle:
    """Build an OKF v0.2 bundle from ontology registries.

    Args:
        name (str): Bundle directory name (typically ``metadata.label`` or
            ``metadata.id``); slugified so the result is filesystem-safe.
        metadata (BaseMetaData): Ontology metadata for the index comment.
        classes (Sequence[OntologyClass]): Ontology classes.
        properties (Sequence[OntologyProperty]): Ontology properties.
        defined_in (Mapping[str, Sequence[str]]): Property id to the class ids
            that declare it.
        context (BaseContext | None): JSON-LD context supplying the namespaces
            for compact IRIs. Defaults to an empty ``BaseContext``.
        closed (Mapping[str, Sequence[str]] | None): Class id to its
            ``sh:ignoredProperties`` for closed (``sh:closed``) shapes. Only
            closed classes appear; defaults to no closed shapes.

    Returns:
        OKFBundle: The in-memory bundle, with the index first and all concept
            documents (and index entries) sorted by id.
    """
    prefixes = _build_prefixes(context if context is not None else BaseContext())
    ordered_classes = sorted(classes, key=lambda c: c.id)
    ordered_properties = sorted(properties, key=lambda p: p.id)
    layout = _Layout.build(
        ordered_classes,
        ordered_properties,
        defined_in,
        prefixes,
        closed or {},
    )
    documents = [_index_document(metadata, ordered_classes, ordered_properties, layout)]
    documents += [_class_document(cls, layout) for cls in ordered_classes]
    documents += [_property_document(prop, layout) for prop in ordered_properties]
    return OKFBundle(name=_slugify(name), documents=documents)
