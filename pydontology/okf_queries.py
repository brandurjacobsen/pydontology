"""Query rdflib graphs to build OKF view dataclasses.

Parses the JSON-LD output of ``ontology_graph()`` and ``shacl_graph()``,
extracts classes, properties, SHACL constraints, and namespace bindings,
and assembles ``IndexView`` / ``ClassView`` / ``PropertyView`` dataclasses
for template rendering.
"""

from collections import deque
from collections.abc import Mapping

from rdflib import RDF, RDFS, OWL, SH, Graph, URIRef

from .okf import (
    CLASS_DIR,
    CLASS_TYPE,
    CONVENTIONS_NOTE,
    PROPERTY_DIR,
    PROPERTY_TYPE,
    ClassView,
    IndexView,
    PrefixEntry,
    PropertyRef,
    PropertyView,
    Reference,
    _local_name,
    _one_line,
    _slugify,
)


# ---------------------------------------------------------------------------
# Graph parsing
# ---------------------------------------------------------------------------


def _parse_graphs(
    onto_jsonld: str,
    shacl_jsonld: str | None,
) -> Graph:
    """Parse ontology and optional SHACL JSON-LD into a single rdflib Graph.

    Args:
        onto_jsonld (str): Ontology graph as JSON-LD text.
        shacl_jsonld (str | None): SHACL graph as JSON-LD text, or None.

    Returns:
        Graph: The merged rdflib graph with namespace bindings accumulated
            from both parses.
    """
    g = Graph()
    g.parse(data=onto_jsonld, format="json-ld")
    if shacl_jsonld:
        g.parse(data=shacl_jsonld, format="json-ld")
    return g


# ---------------------------------------------------------------------------
# Namespace extraction
# ---------------------------------------------------------------------------


def _extract_namespaces(graph: Graph) -> list[PrefixEntry]:
    """Extract namespace prefix bindings from the graph.

    Args:
        graph (Graph): An rdflib graph with namespace_manager populated.

    Returns:
        list[PrefixEntry]: Prefix entries sorted by name.
    """
    entries: list[PrefixEntry] = []
    for prefix, namespace in graph.namespace_manager.namespaces():
        entries.append(PrefixEntry(name=prefix, namespace=str(namespace)))
    return sorted(entries, key=lambda e: e.name)


# ---------------------------------------------------------------------------
# Class queries
# ---------------------------------------------------------------------------


def _query_classes(graph: Graph) -> list[dict]:
    """Extract all RDFS/OWL classes from the graph.

    Args:
        graph (Graph): The parsed ontology graph.

    Returns:
        list[dict]: One dict per class with keys ``uriref``, ``label``,
            ``comment``, ``parents``, ``equivalents``.
    """
    class_types = {RDFS.Class, OWL.Class}
    classes: list[dict] = []

    for cls_uri in graph.subjects(RDF.type, RDFS.Class):
        classes.append(_extract_class(graph, cls_uri))
    for cls_uri in graph.subjects(RDF.type, OWL.Class):
        if cls_uri not in {c["uriref"] for c in classes}:
            classes.append(_extract_class(graph, cls_uri))

    # Sort by IRI for deterministic output
    classes.sort(key=lambda c: c["uriref"])
    return classes


def _extract_class(graph: Graph, cls_uri: URIRef) -> dict:
    """Extract data for a single class node.

    Args:
        graph (Graph): The parsed ontology graph.
        cls_uri (URIRef): The class subject IRI.

    Returns:
        dict: Class data dict.
    """
    uriref = str(cls_uri)

    label = graph.value(cls_uri, RDFS.label)
    comment = graph.value(cls_uri, RDFS.comment)

    parents: list[str] = []
    for parent in graph.objects(cls_uri, RDFS.subClassOf):
        if isinstance(parent, URIRef):
            parents.append(str(parent))
        # Blank nodes (restrictions) are skipped

    equivalents: list[str] = []
    for equiv in graph.objects(cls_uri, OWL.equivalentClass):
        if isinstance(equiv, URIRef):
            equivalents.append(str(equiv))

    return {
        "uriref": uriref,
        "label": str(label) if label is not None else None,
        "comment": str(comment) if comment is not None else None,
        "parents": parents,
        "equivalents": equivalents,
    }


# ---------------------------------------------------------------------------
# Property queries
# ---------------------------------------------------------------------------


def _query_properties(graph: Graph) -> list[dict]:
    """Extract all OWL properties from the graph.

    Args:
        graph (Graph): The parsed ontology graph.

    Returns:
        list[dict]: One dict per property with keys ``uriref``, ``label``,
            ``comment``, ``domains``, ``ranges``, ``types``,
            ``super_property``, ``equivalent_property``, ``inverse_of``.
    """
    property_types = {
        OWL.ObjectProperty,
        OWL.DatatypeProperty,
        OWL.TransitiveProperty,
        OWL.SymmetricProperty,
        OWL.FunctionalProperty,
        OWL.InverseFunctionalProperty,
    }

    properties: list[dict] = []
    seen: set[str] = set()

    for prop_type in property_types:
        for prop_uri in graph.subjects(RDF.type, prop_type):
            uriref = str(prop_uri)
            if uriref in seen:
                continue
            seen.add(uriref)
            properties.append(_extract_property(graph, prop_uri))

    properties.sort(key=lambda p: p["uriref"])
    return properties


def _extract_property(graph: Graph, prop_uri: URIRef) -> dict:
    """Extract data for a single property node.

    Args:
        graph (Graph): The parsed ontology graph.
        prop_uri (URIRef): The property subject IRI.

    Returns:
        dict: Property data dict.
    """
    uriref = str(prop_uri)

    label = graph.value(prop_uri, RDFS.label)
    comment = graph.value(prop_uri, RDFS.comment)

    domains: list[str] = []
    for domain in graph.objects(prop_uri, RDFS.domain):
        if isinstance(domain, URIRef):
            domains.append(str(domain))

    ranges: list[str] = []
    for range_ in graph.objects(prop_uri, RDFS.range):
        if isinstance(range_, URIRef):
            ranges.append(str(range_))

    types: list[str] = []
    for t in graph.objects(prop_uri, RDF.type):
        types.append(str(t))

    super_property = graph.value(prop_uri, RDFS.subPropertyOf)
    equivalent_property = graph.value(prop_uri, OWL.equivalentProperty)
    inverse_of = graph.value(prop_uri, OWL.inverseOf)

    return {
        "uriref": uriref,
        "label": str(label) if label is not None else None,
        "comment": str(comment) if comment is not None else None,
        "domains": domains,
        "ranges": ranges,
        "types": types,
        "super_property": str(super_property) if isinstance(super_property, URIRef) else None,
        "equivalent_property": str(equivalent_property) if isinstance(equivalent_property, URIRef) else None,
        "inverse_of": str(inverse_of) if isinstance(inverse_of, URIRef) else None,
    }


# ---------------------------------------------------------------------------
# Metadata query
# ---------------------------------------------------------------------------


def _query_metadata(graph: Graph) -> str | None:
    """Extract the ontology comment from the owl:Ontology node.

    Args:
        graph (Graph): The parsed ontology graph.

    Returns:
        str | None: The ontology comment, or None if not found.
    """
    for onto_uri in graph.subjects(RDF.type, OWL.Ontology):
        comment = graph.value(onto_uri, RDFS.comment)
        if comment is not None:
            return str(comment)
    return None


# ---------------------------------------------------------------------------
# SHACL queries
# ---------------------------------------------------------------------------


def _query_shacl(graph: Graph) -> dict[str, dict]:
    """Extract SHACL node shape constraints.

    Args:
        graph (Graph): The parsed graph (ontology + SHACL merged).

    Returns:
        dict[str, dict]: Class IRI string to a dict with keys ``closed``
            (bool) and ``ignored`` (list[str]). Only present for classes
            that have an associated ``sh:NodeShape``.
    """
    shapes: dict[str, dict] = {}

    for shape in graph.subjects(RDF.type, SH.NodeShape):
        target = graph.value(shape, SH.targetClass)
        if target is None or not isinstance(target, URIRef):
            continue

        target_iri = str(target)
        closed_val = graph.value(shape, SH.closed)
        closed = _bool_value(closed_val)

        ignored: list[str] = []
        ignored_list = graph.value(shape, SH.ignoredProperties)
        if ignored_list is not None:
            ignored = _rdf_list_items(graph, ignored_list)

        shapes[target_iri] = {"closed": closed, "ignored": ignored}

    return shapes


def _bool_value(value) -> bool:
    """Convert an rdflib literal to a Python bool.

    Args:
        value: An rdflib Literal or bool.

    Returns:
        bool: True if the value represents a truthy boolean.
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1")


def _rdf_list_items(graph: Graph, list_node) -> list[str]:
    """Walk an RDF list (rdf:first / rdf:rest chain) and return string items.

    Args:
        graph (Graph): The rdflib graph.
        list_node: The head node of the RDF list.

    Returns:
        list[str]: The items in list order as strings.
    """
    items: list[str] = []
    current = list_node
    while current is not None and current != RDF.nil:
        first = graph.value(current, RDF.first)
        if first is not None:
            items.append(str(first))
        current = graph.value(current, RDF.rest)
    return items


# ---------------------------------------------------------------------------
# Hierarchy and membership
# ---------------------------------------------------------------------------


def _build_class_hierarchy(
    classes: list[dict],
) -> dict[str, tuple[str, ...]]:
    """Build a class hierarchy from ``rdfs:subClassOf`` triples.

    Args:
        classes (list[dict]): Class data dicts from ``_query_classes``.

    Returns:
        dict[str, tuple[str, ...]]: Class IRI to ordered parent IRIs (only
            parents that are also in the classes list).
    """
    class_iris = {c["uriref"] for c in classes}
    parents: dict[str, tuple[str, ...]] = {}

    for cls in classes:
        seen: dict[str, None] = {}
        for parent in cls["parents"]:
            if parent in class_iris and parent != cls["uriref"] and parent not in seen:
                seen[parent] = None
        parents[cls["uriref"]] = tuple(seen)

    return parents


def _ancestors(
    start: str,
    parents: Mapping[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Return a class's bundled ancestors in breadth-first (nearest-first) order.

    Args:
        start (str): The class IRI to walk up from.
        parents (Mapping[str, tuple[str, ...]]): Class IRI to parent IRIs.

    Returns:
        tuple[str, ...]: Ancestor IRIs, deduplicated and cycle-safe.
    """
    order: list[str] = []
    seen = {start}
    queue: deque[str] = deque(parents.get(start, ()))
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        order.append(node)
        queue.extend(parents.get(node, ()))
    return tuple(order)


def _build_membership(
    classes: list[dict],
    properties: list[dict],
    parents: dict[str, tuple[str, ...]],
    defined_in: dict[str, list[str]],
) -> dict[str, list[tuple[str, str | None]]]:
    """Build the class-membership index: class IRI to applicable properties.

    Own-declared properties come first, then inherited ones keyed by the
    nearest declaring ancestor. Property declaration is determined by
    ``rdfs:domain`` triples, supplemented by ``defined_in`` for multi-class
    properties where domain is suppressed.

    Args:
        classes (list[dict]): Class data dicts.
        properties (list[dict]): Property data dicts.
        parents (dict[str, tuple[str, ...]]): Class IRI to parent IRIs.
        defined_in (dict[str, list[str]]): Property IRI to list of class
            IRIs that declare it (from ``_prop_db``).

    Returns:
        dict[str, list[tuple[str, str | None]]]: Class IRI to list of
            (property_iri, inherited_from_iri_or_None) tuples, ordered
            own-first, id-sorted within each group.
    """
    # Which properties are declared on which classes:
    # first from rdfs:domain, then supplement with defined_in
    declared: dict[str, list[str]] = {}
    for prop in properties:
        for domain in prop["domains"]:
            declared.setdefault(domain, []).append(prop["uriref"])

    # Supplement with defined_in (keyed by property local name → class local names).
    # Build lookup tables from local name → IRI.
    if defined_in:
        prop_by_name = {_local_name(p["uriref"]): p["uriref"] for p in properties}
        cls_by_name = {_local_name(c["uriref"]): c["uriref"] for c in classes}
        for prop_name, class_names in defined_in.items():
            prop_iri = prop_by_name.get(prop_name)
            if prop_iri is None:
                continue
            for class_name in class_names:
                class_iri = cls_by_name.get(class_name)
                if class_iri is not None and prop_iri not in declared.get(class_iri, ()):
                    declared.setdefault(class_iri, []).append(prop_iri)

    membership: dict[str, list[tuple[str, str | None]]] = {}

    for cls in classes:
        class_iri = cls["uriref"]
        own = sorted(declared.get(class_iri, ()))
        members: list[tuple[str, str | None]] = [(pid, None) for pid in own]
        seen = set(own)

        for ancestor in _ancestors(class_iri, parents):
            for pid in sorted(declared.get(ancestor, ())):
                if pid not in seen:
                    seen.add(pid)
                    members.append((pid, ancestor))

        membership[class_iri] = members

    return membership


# ---------------------------------------------------------------------------
# IRI and path helpers
# ---------------------------------------------------------------------------


def _display_name(uriref_str: str, graph: Graph) -> str:
    """Get a human-readable display name for a concept IRI.

    Tries the namespace manager for prefix compaction first, then falls
    back to the local-name portion of the IRI.

    Args:
        uriref_str (str): The URI string.
        graph (Graph): The rdflib graph with namespace bindings.

    Returns:
        str: A display name, e.g. ``"owl:Thing"`` or ``"Person"``.
    """
    try:
        uri = URIRef(uriref_str)
        result = graph.namespace_manager.qname(uri)
        if result is not None:
            prefix, _namespace, localname = result
            if prefix:
                return f"{prefix}:{localname}"
    except Exception:
        pass
    return _local_name(uriref_str)


def _compute_paths(
    urirefs: list[str],
    graph: Graph,
    directory: str,
) -> dict[str, str]:
    """Map concept IRIs to bundle-relative file paths.

    Args:
        urirefs (list[str]): Concept IRI strings.
        graph (Graph): The rdflib graph (for namespace-based local-name
            extraction).
        directory (str): Group directory, e.g. ``"classes"``.

    Returns:
        dict[str, str]: IRI to ``<directory>/<slug>.md`` path.

    Raises:
        ValueError: If two IRIs collapse to the same slug.
    """
    paths: dict[str, str] = {}
    seen: dict[str, str] = {}
    for uriref in urirefs:
        slug = _slugify(_local_name(uriref))
        if slug in seen:
            raise ValueError(
                f"Concept filename collision in '{directory}': "
                f"{seen[slug]!r} and {uriref!r} both map to {slug!r}"
            )
        seen[slug] = uriref
        paths[uriref] = f"{directory}/{slug}.md"
    return paths


# ---------------------------------------------------------------------------
# Reference builders
# ---------------------------------------------------------------------------


def _build_reference(
    uriref: str,
    title: str | None,
    path_lookup: dict[str, str],
    graph: Graph,
) -> Reference:
    """Build a Reference for a concept, linking internal targets.

    Args:
        uriref (str): The concept IRI string.
        title (str | None): Display title; falls back to a compact/local name.
        path_lookup (dict[str, str]): Combined class and property path map.
        graph (Graph): The rdflib graph (for display-name compaction).

    Returns:
        Reference: The populated reference.
    """
    path = path_lookup.get(uriref)
    return Reference(
        uriref=uriref,
        title=title or _display_name(uriref, graph),
        path=path,
    )


def _build_index_reference(
    uriref: str,
    title: str | None,
    comment: str | None,
    path_lookup: dict[str, str],
    graph: Graph,
) -> Reference:
    """Build a Reference for an index listing entry.

    Args:
        uriref (str): The concept IRI string.
        title (str | None): Display title.
        comment (str | None): One-line comment for the index listing.
        path_lookup (dict[str, str]): Combined class and property path map.
        graph (Graph): The rdflib graph (for display-name compaction).

    Returns:
        Reference: The populated reference with an optional comment.
    """
    path = path_lookup.get(uriref)
    return Reference(
        uriref=uriref,
        title=title or _display_name(uriref, graph),
        path=path,
        comment=_one_line(comment),
    )


# ---------------------------------------------------------------------------
# View assembly
# ---------------------------------------------------------------------------


def _build_views(
    graph: Graph,
    classes: list[dict],
    properties: list[dict],
    shacl_data: dict[str, dict],
    parents: dict[str, tuple[str, ...]],
    membership: dict[str, list[tuple[str, str | None]]],
    defined_in: dict[str, list[str]],
) -> tuple[IndexView, list[ClassView], list[PropertyView]]:
    """Assemble IndexView, ClassView, and PropertyView dataclasses.

    Args:
        graph (Graph): The parsed rdflib graph (for namespace lookups).
        classes (list[dict]): Class data from ``_query_classes``.
        properties (list[dict]): Property data from ``_query_properties``.
        shacl_data (dict[str, dict]): SHACL data from ``_query_shacl``.
        parents (dict[str, tuple[str, ...]]): Class hierarchy.
        membership (dict[str, list[tuple[str, str | None]]]): Class→property
            membership index.
        defined_in (dict[str, list[str]]): Property name → declaring class
            names, for populating ``# Defined in`` on multi-class properties.

    Returns:
        tuple[IndexView, list[ClassView], list[PropertyView]]: The assembled
            index, class, and property views.
    """
    # --- Path computation ---
    class_paths = _compute_paths([c["uriref"] for c in classes], graph, CLASS_DIR)
    property_paths = _compute_paths([p["uriref"] for p in properties], graph, PROPERTY_DIR)
    all_paths = {**class_paths, **property_paths}

    # --- Index view ---
    ontology_comment = _query_metadata(graph)

    index_classes: list[Reference] = []
    for cls in classes:
        ref = _build_index_reference(
            cls["uriref"], cls["label"], cls["comment"], all_paths, graph
        )
        index_classes.append(ref)

    index_properties: list[Reference] = []
    for prop in properties:
        ref = _build_index_reference(
            prop["uriref"], prop["label"], prop["comment"], all_paths, graph
        )
        index_properties.append(ref)

    index_view = IndexView(
        path="index.md",
        frontmatter={"okf_version": "0.2"},
        comment=_one_line(ontology_comment),
        prefixes=_extract_namespaces(graph),
        conventions_note=CONVENTIONS_NOTE,
        classes=index_classes,
        properties=index_properties,
    )

    # --- Class views ---
    class_views: list[ClassView] = []
    for cls in classes:
        class_iri = cls["uriref"]

        # Subclass references
        sub_of: list[Reference] = []
        for parent_iri in parents.get(class_iri, ()):
            sub_of.append(_build_reference(parent_iri, None, all_paths, graph))
        # Also include parents not in the bundle (e.g. owl:Thing)
        for parent_iri in cls["parents"]:
            if parent_iri not in parents.get(class_iri, ()):
                sub_of.append(_build_reference(parent_iri, None, all_paths, graph))

        # Equivalent class references
        equiv: list[Reference] = []
        for equiv_iri in cls["equivalents"]:
            equiv.append(_build_reference(equiv_iri, None, all_paths, graph))

        # Property references (own first, then inherited)
        props: list[PropertyRef] = []
        for prop_iri, inherited_from in membership.get(class_iri, ()):
            prop_path = property_paths.get(prop_iri, "")
            prop_label = _local_name(prop_iri)
            inherited_ref = None
            if inherited_from is not None:
                inherited_ref = _build_reference(inherited_from, None, all_paths, graph)
            props.append(
                PropertyRef(
                    uriref=prop_iri,
                    title=prop_label,
                    path=prop_path,
                    inherited_from=inherited_ref,
                )
            )

        # SHACL data
        shacl = shacl_data.get(class_iri, {})
        closed = shacl.get("closed", False)
        ignored = shacl.get("ignored", [])

        class_views.append(
            ClassView(
                path=class_paths[class_iri],
                frontmatter={
                    "type": CLASS_TYPE,
                    "title": cls["label"] or _local_name(class_iri),
                    "resource": _display_name(class_iri, graph),
                },
                comment=_one_line(cls["comment"]),
                uriref=class_iri,
                sub_class_of=sub_of,
                equivalent_class=equiv,
                properties=props,
                closed=closed,
                ignored_properties=ignored,
            )
        )

    # --- Property views ---
    property_views: list[PropertyView] = []
    for prop in properties:
        prop_iri = prop["uriref"]

        # Domain references
        domain_ref = None
        if prop["domains"]:
            domain_iri = prop["domains"][0]
            domain_ref = _build_reference(domain_iri, None, all_paths, graph)

        # Range references
        range_ref = None
        if prop["ranges"]:
            range_iri = prop["ranges"][0]
            range_ref = _build_reference(range_iri, None, all_paths, graph)

        # Super-property reference
        super_ref = None
        if prop["super_property"] is not None:
            super_ref = _build_reference(prop["super_property"], None, all_paths, graph)

        # Equivalent property reference
        equiv_ref = None
        if prop["equivalent_property"] is not None:
            equiv_ref = _build_reference(prop["equivalent_property"], None, all_paths, graph)

        # Inverse-of reference
        inv_ref = None
        if prop["inverse_of"] is not None:
            inv_ref = _build_reference(prop["inverse_of"], None, all_paths, graph)

        # Defined-in references (classes that declare this property via rdfs:domain
        # or via the defined_in side-channel for multi-class properties)
        defined: list[Reference] = []
        for domain_iri in prop["domains"]:
            defined.append(_build_reference(domain_iri, None, all_paths, graph))
        # Supplement with defined_in for multi-class properties
        prop_name = _local_name(prop_iri)
        cls_by_name = {_local_name(c["uriref"]): c["uriref"] for c in classes}
        for class_name in defined_in.get(prop_name, ()):
            class_iri = cls_by_name.get(class_name)
            if class_iri is not None and class_iri not in {ref.uriref for ref in defined}:
                defined.append(_build_reference(class_iri, None, all_paths, graph))

        property_views.append(
            PropertyView(
                path=property_paths[prop_iri],
                frontmatter={
                    "type": PROPERTY_TYPE,
                    "title": prop["label"] or _local_name(prop_iri),
                    "resource": _display_name(prop_iri, graph),
                },
                comment=_one_line(prop["comment"]),
                uriref=prop_iri,
                types=prop["types"],
                domain=domain_ref,
                range=range_ref,
                sub_property_of=super_ref,
                equivalent_property=equiv_ref,
                inverse_of=inv_ref,
                defined_in=defined,
            )
        )

    return (index_view, class_views, property_views)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def query_ontology(
    onto_jsonld: str,
    shacl_jsonld: str | None = None,
    *,
    defined_in: dict[str, list[str]] | None = None,
) -> tuple[IndexView, list[ClassView], list[PropertyView]]:
    """Query ontology and SHACL graphs and build OKF view dataclasses.

    Args:
        onto_jsonld (str): Serialized ontology graph as JSON-LD text.
        shacl_jsonld (str | None): Serialized SHACL graph as JSON-LD text,
            or None if no SHACL data is available.
        defined_in (dict[str, list[str]] | None): Property IRI to list of
            class IRIs that declare it. Supplements ``rdfs:domain`` for
            multi-class properties where domain is suppressed.

    Returns:
        tuple: ``(index_view, class_views, property_views, namespace_manager)``.
    """
    graph = _parse_graphs(onto_jsonld, shacl_jsonld)
    classes = _query_classes(graph)
    properties = _query_properties(graph)
    shacl_data = _query_shacl(graph) if shacl_jsonld else {}
    parents = _build_class_hierarchy(classes)
    membership = _build_membership(classes, properties, parents, defined_in or {})

    views = _build_views(
        graph=graph,
        classes=classes,
        properties=properties,
        shacl_data=shacl_data,
        parents=parents,
        membership=membership,
        defined_in=defined_in or {},
    )
    return (*views, graph.namespace_manager)