import json
import re
from collections.abc import Mapping
from os import PathLike
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


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
