"""IRI types and helpers.

Two flavours of IRI-typed string are used across the codebase:

- ``AnyIri`` is strict: it must parse as an RFC 3987 IRI (i.e. carry a
  scheme). It is used on graph models that Pydontology constructs itself,
  because those ids are qualified before the model is built.
- ``IriRef`` is an IRI *reference*: it additionally accepts relative names
  (``knows``) and compact IRIs (``ex:knows``). It is used on authoring-facing
  models (``Entity``, ``Relation``, annotations) whose bare names can only be
  qualified once ``Settings.DEFAULT_PREFIX`` is known. If a ``DEFAULT_PREFIX``
  is configured, ``IriRef`` values are qualified automatically on
  serialization.
"""

from typing import Annotated

import rfc3987
from pydantic import AfterValidator, PlainSerializer

from .settings import Settings
from .validators import val_iri, val_iri_ref

# The active prefix is process-wide, mirroring the existing global Entity
# serialization flags. Pydontology updates it from Settings via
# set_default_prefix(). It is seeded from the Settings default so that
# standalone Entity serialization behaves sensibly.
_default_prefix: str | None = Settings().DEFAULT_PREFIX


def set_default_prefix(prefix: str | None) -> None:
    """Set the process-wide default prefix used to qualify bare names."""
    global _default_prefix
    _default_prefix = prefix


def get_default_prefix() -> str | None:
    """Return the process-wide default prefix (may be None)."""
    return _default_prefix


def _is_absolute_iri(value: str) -> bool:
    try:
        rfc3987.parse(value, rule="IRI")
        return True
    except ValueError:
        return False


# Sentinel distinguishing "no prefix argument" (use the process-wide default)
# from an explicit prefix=None (meaning: bare names must be rejected).
_UNSET = object()


def qualify_iri(value: str, prefix: str | None | object = _UNSET) -> str:
    """Qualify a relative name with the configured prefix.

    Values that already parse as an IRI (absolute or compact, e.g.
    ``http://x/y``, ``owl:Thing``, ``ex:knows``) are returned unchanged, so
    this function is idempotent. Bare names are prefixed; if ``prefix`` (or
    the process-wide default) is unset, a ValueError is raised.
    """
    value = value.strip()
    if _is_absolute_iri(value):
        return value

    if prefix is _UNSET:
        prefix = _default_prefix
    if not prefix:
        raise ValueError(
            f"'{value}' is not an absolute IRI and no DEFAULT_PREFIX is set. "
            "Supply a qualified IRI (e.g. 'ex:name'), a serialization_alias, "
            "or set Settings.DEFAULT_PREFIX."
        )

    # A namespace-style prefix is concatenated directly; a compact prefix is
    # joined with a single colon.
    if prefix.endswith(("/", "#")):
        return f"{prefix}{value}"
    return f"{prefix.rstrip(':')}:{value}"


AnyIri = Annotated[str, AfterValidator(val_iri)]

IriRef = Annotated[
    str,
    AfterValidator(val_iri_ref),
    PlainSerializer(qualify_iri, return_type=str),
]