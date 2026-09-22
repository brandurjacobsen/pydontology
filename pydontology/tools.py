"""LLM description callables built from a Pydontology instance's registries.

Requires the optional ``tools`` extra (``pip install pydontology[tools]``).
"""

from typing import Callable

try:
    import jinja2
except ImportError as e:
    raise ImportError(
        "pydontology.tools requires jinja2. Install it with `pip install pydontology[tools]`."
    ) from e

from .iri import qualify_iri
from .models import OntologyClass, OntologyProperty, RDFList, Relation, Restriction
from .pydontology import Pydontology


def _relation_id(value: Relation | Restriction | str | None) -> str | None:
    """Reduce a Relation, Restriction, or str to a plain (qualified) IRI string."""
    if value is None:
        return None
    if isinstance(value, Relation):
        return qualify_iri(value.id)
    if isinstance(value, Restriction):
        return qualify_iri(value.id) if value.id else "owl:Restriction"
    return qualify_iri(str(value))


def _relation_ids(values: list[Relation | Restriction | str]) -> list[str] | None:
    ids = [i for i in (_relation_id(v) for v in values) if i is not None]
    return ids or None


def _class_context(cls: OntologyClass) -> dict[str, object]:
    """Flatten an OntologyClass to plain values for template rendering.

    All keys are always present (with None/empty values) so template lookups
    never fall back to Jinja's built-in globals (e.g. 'range').
    """
    intersection = cls.intersectionOf
    if intersection is not None:
        members = intersection.list if isinstance(intersection, RDFList) else list(intersection)
        intersection_of = _relation_ids(members)
    else:
        intersection_of = None
    return {
        "id": cls.id,
        "type": cls.type,
        "label": cls.label,
        "comment": cls.comment,
        "subClassOf": _relation_ids(cls.subClassOf) if cls.subClassOf else None,
        "equivalentClass": (
            _relation_ids(cls.equivalentClass) if cls.equivalentClass else None
        ),
        "seeAlso": str(cls.seeAlso) if cls.seeAlso else None,
        "isDefinedBy": str(cls.isDefinedBy) if cls.isDefinedBy else None,
        "intersectionOf": intersection_of,
    }


def _property_context(prop: OntologyProperty) -> dict[str, object]:
    """Flatten an OntologyProperty to plain values for template rendering.

    All keys are always present (with None/empty values) so template lookups
    never fall back to Jinja's built-in globals (e.g. 'range').
    """
    return {
        "id": prop.id,
        "type": prop.type,
        "label": prop.label,
        "comment": prop.comment,
        "domain": _relation_id(prop.domain),
        "range": _relation_id(prop.range),
        "subPropertyOf": _relation_id(prop.subPropertyOf),
        "equivalentProperty": _relation_id(prop.equivalentProperty),
        "inverseOf": _relation_id(prop.inverseOf),
        "seeAlso": str(prop.seeAlso) if prop.seeAlso else None,
        "isDefinedBy": str(prop.isDefinedBy) if prop.isDefinedBy else None,
    }


CLASS_TEMPLATE = """\
Class: {{ label or id }}
{% if comment %}
Comment: {{ comment }}
{% endif %}
IRI: {{ id }}
{% if subClassOf %}
Subclass of: {{ subClassOf | join(", ") }}
{% endif %}
{% if equivalentClass %}
Equivalent to: {{ equivalentClass | join(", ") }}
{% endif %}
{% if intersectionOf %}
Intersection of: {{ intersectionOf | join(", ") }}
{% endif %}
{% if seeAlso %}
See also: {{ seeAlso }}
{% endif %}
{% if isDefinedBy %}
Defined by: {{ isDefinedBy }}
{% endif %}
"""

PROPERTY_TEMPLATE = """\
Property: {{ label or id }}
{% if comment %}
Comment: {{ comment }}
{% endif %}
IRI: {{ id }}
Type: {{ type | join(", ") }}
{% if domain %}
Domain: {{ domain }}
{% endif %}
{% if range %}
Range: {{ range }}
{% endif %}
{% if subPropertyOf %}
Subproperty of: {{ subPropertyOf }}
{% endif %}
{% if equivalentProperty %}
Equivalent to: {{ equivalentProperty }}
{% endif %}
{% if inverseOf %}
Inverse of: {{ inverseOf }}
{% endif %}
{% if seeAlso %}
See also: {{ seeAlso }}
{% endif %}
{% if isDefinedBy %}
Defined by: {{ isDefinedBy }}
{% endif %}
"""

DEFAULT_TEMPLATES: dict[str, str] = {
    "class": CLASS_TEMPLATE,
    "property": PROPERTY_TEMPLATE,
}


def _local_name(iri: str) -> str | None:
    """Return the local part of a compact IRI (e.g. 'Employee' for 'ex:Employee')."""
    if ":" not in iri:
        return None
    tail = iri.rsplit(":", 1)[1]
    if "/" in tail or "#" in tail:
        return None
    return tail or None


def _index(objs):
    """Index ontology nodes by full IRI and, when possible, by local name."""
    index = {}
    for obj in objs:
        index[obj.id] = obj
        local = _local_name(obj.id)
        if local:
            index.setdefault(local, obj)
    return index


def llm_tools(
    onto: Pydontology,
    templates: dict[str, str] | None = None,
) -> dict[str, Callable[[str], str]]:
    """Build LLM description callables from a Pydontology instance.

    Returns a dict of plain callables, ready to hand to an LLM client:

    - ``"get_class_description"``: ``class_id: str -> str``
    - ``"get_property_description"``: ``property_id: str -> str``

    Output is rendered with Jinja2. ``templates`` optionally overrides the
    built-in defaults, keyed by ``"class"`` and ``"property"``.
    """
    if templates:
        unknown = set(templates) - set(DEFAULT_TEMPLATES)
        if unknown:
            raise ValueError(f"Unknown template key(s): {sorted(unknown)}")

    class_index = _index(onto.classes)
    property_index = _index(onto.properties)

    merged = {**DEFAULT_TEMPLATES, **templates} if templates else DEFAULT_TEMPLATES
    env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, autoescape=False)
    class_template = env.from_string(merged["class"])
    property_template = env.from_string(merged["property"])

    def get_class_description(class_id: str) -> str:
        """Describe an ontology class by its id."""
        cls = class_index.get(class_id)
        if cls is None:
            return f"Class '{class_id}' not found."
        return class_template.render(**_class_context(cls)).strip()

    def get_property_description(property_id: str) -> str:
        """Describe an ontology property by its id."""
        prop = property_index.get(property_id)
        if prop is None:
            return f"Property '{property_id}' not found."
        return property_template.render(**_property_context(prop)).strip()

    return {
        "get_class_description": get_class_description,
        "get_property_description": get_property_description,
    }
