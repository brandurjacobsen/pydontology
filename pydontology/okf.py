import json
import re
from dataclasses import dataclass, field
from enum import Enum
from os import PathLike
from pathlib import Path

try:
    import jinja2
except ImportError:
    jinja2 = None  # type: ignore[assignment]

from pydantic import BaseModel, ConfigDict, Field

from .models import BaseMetaData, JSONLDGraph


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLASS_TYPE = "Ontology Class"
PROPERTY_TYPE = "Ontology Property"
CLASS_DIR = "classes"
PROPERTY_DIR = "properties"


class MembershipMode(str, Enum):
    """Controls how property→class membership is determined.

    ``PYDONTOLOGY`` (default) uses the ``_prop_db`` internal registry,
    treating classes as schemas where properties belong to specific
    classes.  ``RDF`` infers membership solely from the graph —
    ``rdfs:domain`` and ``sh:targetClass`` / ``sh:property`` / ``sh:path``
    — treating properties as global.
    """

    PYDONTOLOGY = "pydontology"
    RDF = "rdf"


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


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


def _local_name(uriref_str: str) -> str:
    """Extract the local-name portion from a URI string.

    Takes the part after the last ``#`` or ``/``. For bare names with no
    separator, returns the string unchanged.

    Args:
        uriref_str (str): The URI string.

    Returns:
        str: The local name.
    """
    for sep in ("#", "/"):
        if sep in uriref_str:
            return uriref_str.rsplit(sep, 1)[-1]
    return uriref_str


# ---------------------------------------------------------------------------
# Document models
# ---------------------------------------------------------------------------


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
        if not self.frontmatter:
            return self.body.strip() + "\n"
        lines = [f"{key}: {json.dumps(value)}" for key, value in self.frontmatter.items()]
        return "---\n" + "\n".join(lines) + "\n---\n\n" + self.body.strip() + "\n"

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


# ---------------------------------------------------------------------------
# View dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Reference:
    """A reference to a class or property concept.

    Attributes:
        uriref (str): The IRI string of the referenced concept.
        title (str): Display title (label or local name).
        path (str | None): Bundle-relative path, or None for external references.
        comment (str | None): Optional one-line comment for index listings.
    """
    uriref: str
    title: str
    path: str | None = None
    comment: str | None = None


@dataclass
class PropertyRef:
    """A reference to a property with inheritance tracking.

    Attributes:
        uriref (str): The IRI string of the property.
        title (str): Display title.
        path (str): Bundle-relative path for this property concept.
        inherited_from (Reference | None): The ancestor class that declares
            the property, or None when declared directly on the current class.
    """
    uriref: str
    title: str
    path: str
    inherited_from: "Reference | None" = None


@dataclass
class PrefixEntry:
    """A namespace prefix entry for the index."""
    name: str
    namespace: str


@dataclass
class ClassView:
    """View model for a class template.

    Attributes:
        path (str): Bundle-relative path, e.g. ``classes/Person.md``.
        frontmatter (dict[str, str]): Frontmatter key-value pairs.
        comment (str | None): One-line class description.
        uriref (str): The class IRI string.
        sub_class_of (list[Reference]): Parent class references.
        equivalent_class (list[Reference]): Equivalent class references.
        required_properties (list[PropertyRef]): Properties that must be
            present (``sh:minCount`` ≥ 1 on this class's NodeShape).
        associated_properties (list[PropertyRef]): All other applicable
            properties, own-declared first then inherited.
        closed (bool): Whether the class shape is ``sh:closed``.
        ignored_properties (list[str]): Ignored properties for closed shapes.
    """
    path: str
    frontmatter: dict[str, str]
    comment: str | None
    uriref: str
    sub_class_of: list[Reference] = field(default_factory=list)
    equivalent_class: list[Reference] = field(default_factory=list)
    required_properties: list[PropertyRef] = field(default_factory=list)
    associated_properties: list[PropertyRef] = field(default_factory=list)
    closed: bool = False
    ignored_properties: list[str] = field(default_factory=list)


@dataclass
class PropertyView:
    """View model for a property template.

    Attributes:
        path (str): Bundle-relative path, e.g. ``properties/name.md``.
        frontmatter (dict[str, str]): Frontmatter key-value pairs.
        comment (str | None): One-line property description.
        uriref (str): The property IRI string.
        types (list[str]): RDF type IRIs (e.g. ``owl:ObjectProperty``).
        domain (Reference | None): RDFS domain class reference.
        range (Reference | None): RDFS range class reference.
        sub_property_of (Reference | None): Super-property reference.
        equivalent_property (Reference | None): Equivalent property reference.
        inverse_of (Reference | None): Inverse property reference.
        required_by (list[Reference]): Classes whose SHACL shapes require
            this property (``sh:minCount`` ≥ 1).
        associated_with (list[Reference]): Classes associated with this
            property via ``rdfs:domain`` or class definitions, without a
            mandatory SHACL constraint.
    """
    path: str
    frontmatter: dict[str, str]
    comment: str | None
    uriref: str
    types: list[str] = field(default_factory=list)
    domain: Reference | None = None
    range: Reference | None = None
    sub_property_of: Reference | None = None
    equivalent_property: Reference | None = None
    inverse_of: Reference | None = None
    required_by: list[Reference] = field(default_factory=list)
    associated_with: list[Reference] = field(default_factory=list)


@dataclass
class IndexView:
    """View model for the index template.

    Attributes:
        path (str): Always ``"index.md"``.
        frontmatter (dict[str, str]): Frontmatter, typically ``okf_version``.
        comment (str | None): One-line ontology description.
        prefixes (list[PrefixEntry]): Namespace prefix entries for the
            copy-pasteable PREFIX block.
        classes (list[Reference]): Class concepts for the index listing.
        properties (list[Reference]): Property concepts for the index listing.
    """
    path: str
    frontmatter: dict[str, str]
    comment: str | None
    prefixes: list[PrefixEntry] = field(default_factory=list)
    classes: list[Reference] = field(default_factory=list)
    properties: list[Reference] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Jinja2 filters
# ---------------------------------------------------------------------------


def _ref_filter(ref: Reference) -> str:
    """Render a Reference as a Markdown link or bare title."""
    if ref.path is not None:
        return f"[{ref.title}](/{ref.path})"
    return ref.title


def _make_compact_iri_filter(ns_manager):
    """Build a ``|compact_iri`` filter closed over an rdflib namespace manager.

    Args:
        ns_manager: An rdflib ``NamespaceManager`` instance.

    Returns:
        callable: A filter that takes a URI string and returns a compact IRI
            (``prefix:localname``) or the full IRI if no prefix matches.
    """
    from rdflib.term import URIRef

    def compact_iri(uriref_str: str) -> str:
        # Resolved-against-filesystem IRIs: show the local name only
        if uriref_str.startswith("file:"):
            return _local_name(uriref_str)
        try:
            uri = URIRef(uriref_str)
            result = ns_manager.qname(uri)
            if result is not None:
                prefix, _namespace, localname = result
                if prefix:
                    return f"{prefix}:{localname}"
        except Exception:
            pass
        return uriref_str

    return compact_iri


def _make_iri_label_filter(ns_manager):
    """Build an ``|iri_label`` filter closed over an rdflib namespace manager.

    Args:
        ns_manager: An rdflib ``NamespaceManager`` instance.

    Returns:
        callable: A filter that takes a URI string and returns ``"IRI"`` when
            the URI can be compacted or is absolute, otherwise ``"Relative IRI"``.
    """
    from rdflib.term import URIRef

    def iri_label(uriref_str: str) -> str:
        # Resolved-against-filesystem IRIs are not real ontology IRIs
        if uriref_str.startswith("file:"):
            return "Relative IRI"
        try:
            uri = URIRef(uriref_str)
            result = ns_manager.qname(uri)
            if result is not None:
                prefix, _namespace, _localname = result
                if prefix:
                    return "IRI"
        except Exception:
            pass
        # Check for absolute IRI (has a scheme with "//")
        if "://" in uriref_str:
            return "IRI"
        # Compact forms like "owl:Thing"
        if ":" in uriref_str and not uriref_str.startswith("_:"):
            return "IRI"
        return "Relative IRI"

    return iri_label


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


def _render_document(
    env: "jinja2.Environment",
    template_name: str,
    view: IndexView | ClassView | PropertyView,
) -> OKFDocument:
    """Render a single Jinja2 template into an OKF document.

    Args:
        env (jinja2.Environment): The Jinja2 environment.
        template_name (str): The template filename, e.g. ``class.md.j2``.
        view (IndexView | ClassView | PropertyView): The view model.

    Returns:
        OKFDocument: The rendered document.
    """
    template = env.get_template(template_name)
    body = template.render(view=view).strip()
    return OKFDocument(path=view.path, frontmatter=view.frontmatter, body=body)


# ---------------------------------------------------------------------------
# Bundle builder (from graphs)
# ---------------------------------------------------------------------------


def build_okf_bundle(
    *,
    name: str,
    onto_graph: JSONLDGraph,
    shacl_graph: JSONLDGraph | None = None,
    defined_in: dict[str, list[str]] | None = None,
    membership_mode: MembershipMode = MembershipMode.PYDONTOLOGY,
    template_dir: str | PathLike | None = None,
) -> OKFBundle:
    """Build an OKF v0.2 bundle from ontology and SHACL graphs.

    Serializes the graphs to JSON-LD, parses them with rdflib, extracts
    classes, properties, and SHACL constraints, and renders the results
    through Jinja2 templates.

    Args:
        name (str): Bundle directory name (typically the slugified ontology
            label or id).
        onto_graph (JSONLDGraph): The ontology graph from ``ontology_graph()``.
        shacl_graph (JSONLDGraph | None): The SHACL graph from
            ``shacl_graph()``, or None.
        defined_in (dict[str, list[str]] | None): Property IRI to list of
            class IRIs that declare it. Supplements ``rdfs:domain`` for
            multi-class properties where domain is not emitted.
        membership_mode (MembershipMode): How to determine property→class
            membership. ``PYDONTOLOGY`` (default) uses the internal field
            registry; ``RDF`` infers everything from the graph.
        template_dir (str | PathLike | None): Directory containing Jinja2
            templates. Defaults to the package's built-in template directory.

    Returns:
        OKFBundle: The in-memory bundle, with the index first and all concept
            documents sorted by IRI.

    Raises:
        ImportError: If ``jinja2`` or ``rdflib`` is not installed.
    """
    if jinja2 is None:
        raise ImportError(
            "jinja2 is required for OKF bundle building. "
            "Install it with: pip install jinja2"
        )

    try:
        import rdflib  # noqa: F401
    except ImportError:
        raise ImportError(
            "rdflib is required for OKF bundle building. "
            "Install it with: pip install rdflib"
        )

    from .okf_queries import query_ontology

    # Serialize graphs to JSON-LD
    onto_jsonld = onto_graph.model_dump_json(exclude_none=True)
    shacl_jsonld = None
    if shacl_graph is not None:
        shacl_jsonld = shacl_graph.model_dump_json(exclude_none=True)

    # Query rdflib for views (also returns the namespace manager for filters)
    index_view, class_views, property_views, ns_manager = query_ontology(
        onto_jsonld, shacl_jsonld, defined_in=defined_in,
        membership_mode=membership_mode,
    )

    # Set up Jinja2 environment
    if template_dir is not None:
        loader: "jinja2.BaseLoader" = jinja2.FileSystemLoader(str(template_dir))
    else:
        loader = jinja2.PackageLoader("pydontology", "templates")
    env = jinja2.Environment(loader=loader, autoescape=False)
    env.filters["compact_iri"] = _make_compact_iri_filter(ns_manager)
    env.filters["iri_label"] = _make_iri_label_filter(ns_manager)
    env.filters["ref"] = _ref_filter

    # Render all documents
    documents: list[OKFDocument] = []
    documents.append(_render_document(env, "index.md.j2", index_view))
    for view in class_views:
        documents.append(_render_document(env, "class.md.j2", view))
    for view in property_views:
        documents.append(_render_document(env, "property.md.j2", view))

    return OKFBundle(name=_slugify(name), documents=documents)
