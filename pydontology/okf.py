import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .models import (
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
    """

    class_paths: Mapping[str, str]
    property_paths: Mapping[str, str]
    class_titles: Mapping[str, str]
    property_titles: Mapping[str, str]
    class_members: Mapping[str, tuple[str, ...]]
    property_members: Mapping[str, tuple[str, ...]]

    @classmethod
    def build(
        cls,
        classes: Sequence[OntologyClass],
        properties: Sequence[OntologyProperty],
        defined_in: Mapping[str, Sequence[str]],
    ) -> "_Layout":
        """Derive a layout from the ontology registries.

        Args:
            classes (Sequence[OntologyClass]): Ontology classes.
            properties (Sequence[OntologyProperty]): Ontology properties.
            defined_in (Mapping[str, Sequence[str]]): Property id to the class
                ids that define it.

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


def _subclass_line(cls: OntologyClass, layout: _Layout) -> str | None:
    """Render the ``Subclass of`` body line for a class.

    Parents that are part of the bundle become markdown links; anything else
    (``owl:Thing``, external IRIs, restrictions) is rendered as plain text.

    Args:
        cls (OntologyClass): The class to render.
        layout (_Layout): Precomputed path and title lookups.

    Returns:
        str | None: The rendered line, or None when the class has no
            superclasses.
    """
    if not cls.subClassOf:
        return None
    rendered = []
    for entry in cls.subClassOf:
        entry_id = _entry_id(entry)
        link = layout.class_link(entry_id)
        rendered.append(f"[{entry_id}]({link})" if link else entry_id)
    return "Subclass of: " + ", ".join(rendered)


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
    blocks.append(f"IRI: {cls.id}")
    subclass = _subclass_line(cls, layout)
    if subclass:
        blocks.append(subclass)

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
            "resource": cls.id,
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
            "resource": prop.id,
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
        layout (_Layout): Precomputed path and title lookups.

    Returns:
        OKFDocument: The index document, carrying only the ``okf_version``
            frontmatter key.
    """
    blocks: list[str] = []
    comment = _one_line(metadata.comment)
    if comment:
        blocks.append(comment)
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

    Returns:
        OKFBundle: The in-memory bundle, with the index first and all concept
            documents (and index entries) sorted by id.
    """
    ordered_classes = sorted(classes, key=lambda c: c.id)
    ordered_properties = sorted(properties, key=lambda p: p.id)
    layout = _Layout.build(ordered_classes, ordered_properties, defined_in)
    documents = [
        _index_document(metadata, ordered_classes, ordered_properties, layout)
    ]
    documents += [_class_document(cls, layout) for cls in ordered_classes]
    documents += [_property_document(prop, layout) for prop in ordered_properties]
    return OKFBundle(name=_slugify(name), documents=documents)
