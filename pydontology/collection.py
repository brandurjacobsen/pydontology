from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, List

from .models import BaseContext, BaseMetaData, JSONLDGraph, Relation
from .pydontology import Pydontology
from .settings import Settings

if TYPE_CHECKING:
    from pydantic_ai.output import ToolOutput


@dataclass
class SubOntology:
    name: str
    description: str
    ontology: Pydontology
    active: bool = True


class PydontologyCollection:
    """Registry of sub-ontologies for ToolOutput export."""

    def __init__(self, metadata: BaseMetaData | None = None) -> None:
        self._sub_ontologies: List[SubOntology] = []
        self.metadata = metadata

    def _check_for_duplicate_ids(self, graph_items: list[Any]) -> None:
        seen_ids: set[str] = set()
        duplicate_ids: list[str] = []

        for item in graph_items:
            data = None
            if hasattr(item, "model_dump"):
                data = item.model_dump(by_alias=True, exclude_none=True)
            elif isinstance(item, dict):
                data = item

            if not data:
                continue

            item_id = data.get("@id") or data.get("id")
            if not item_id:
                continue

            if item_id in seen_ids:
                if item_id not in duplicate_ids:
                    duplicate_ids.append(item_id)
                continue

            seen_ids.add(item_id)

        if duplicate_ids:
            duplicates = ", ".join(duplicate_ids)
            raise ValueError(
                f"Duplicate @id values found in ontology graph: {duplicates}"
            )

    def _name_from_metadata_id(self, metadata_id: str) -> str | None:
        if not metadata_id:
            return None
        if "#" in metadata_id:
            candidate = metadata_id.rsplit("#", 1)[-1]
        else:
            candidate = metadata_id.rsplit("/", 1)[-1]
        return candidate or None

    def _derive_name_description(
        self,
        *,
        ontology: Pydontology,
        module_stem: str,
        var_name: str | None,
        module_doc: str | None,
        multiple: bool,
    ) -> tuple[str, str]:
        name = None
        description = None

        if ontology.metadata is not None:
            name = self._name_from_metadata_id(ontology.metadata.id)
            description = ontology.metadata.comment or ontology.metadata.label

        if not name:
            if multiple and var_name:
                name = f"{module_stem}_{var_name}"
            else:
                name = module_stem

        if not description:
            description = module_doc or f"{name} ontology"

        return name, description

    def register_from_folder(
        self, path: str | Path, pattern: str = "*.py"
    ) -> list[str]:
        """Register Pydontology instances from a folder of modules."""

        folder = Path(path)
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Folder not found: {folder}")

        registered: list[str] = []
        module_paths = sorted(folder.glob(pattern))
        for index, module_path in enumerate(module_paths):
            if module_path.name == "__init__.py":
                continue

            module_base = re.sub(r"\W+", "_", module_path.stem)
            module_name = f"_pydontology_sub_{module_base}_{index}"
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to load module from {module_path}")

            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as exc:
                raise ImportError(
                    f"Failed to import module {module_path}: {exc}"
                ) from exc

            instances: list[tuple[str, Pydontology]] = []
            for var_name, value in vars(module).items():
                if isinstance(value, Pydontology):
                    instances.append((var_name, value))

            if not instances:
                raise ValueError(f"No Pydontology instances found in {module_path}")

            module_doc = module.__doc__.strip() if module.__doc__ else None
            multiple = len(instances) > 1
            for var_name, ontology in instances:
                name, description = self._derive_name_description(
                    ontology=ontology,
                    module_stem=module_path.stem,
                    var_name=var_name,
                    module_doc=module_doc,
                    multiple=multiple,
                )
                self.register(name=name, ontology=ontology, description=description)
                registered.append(name)

        return registered

    def register(self, name: str, ontology: Pydontology, description: str) -> None:
        """Register a sub-ontology with a description."""

        if any(item.name == name for item in self._sub_ontologies):
            raise ValueError(f"Sub-ontology '{name}' already registered")
        self._sub_ontologies.append(
            SubOntology(name=name, description=description, ontology=ontology)
        )

    def activate(self, name: str) -> SubOntology | None:
        """Set a sub-ontology as active in the collection"""
        for s in self._sub_ontologies:
            if s.name == name:
                s.active = True
                return s
        return None

    def deactivate(self, name: str) -> SubOntology | None:
        "Set a sub-ontology as inactive in the collection"
        for s in self._sub_ontologies:
            if s.name == name:
                s.active = False
                return s
        return None

    def tool_outputs(
        self,
        context: BaseContext = BaseContext(),
        settings: Settings = Settings(),
    ) -> list[ToolOutput]:
        """Return Pydantic AI ToolOutput objects built from each sub-ontology schema.

        Include owl:Ontology object in description if it exists in sub-ontology
        """
        try:
            from pydantic_ai.output import ToolOutput
        except ImportError as exc:
            # Keep pydantic-ai optional; surface a helpful install hint.
            raise ImportError(
                "pydantic-ai is required for ToolOutput support. Install with: pip install pydontology[ai]"
            ) from exc

        outputs = []
        for sub in self._sub_ontologies:
            if not sub.active:
                continue
            schema_model = sub.ontology.schema_graph(
                name=sub.name, context=context, settings=settings
            )
            if sub.ontology.metadata is not None:
                description = f"""{sub.description}\nAssociated owl:Ontology as json-ld:\n{sub.ontology.metadata.model_dump_json(indent=2, exclude_none=True)}"""
            else:
                description = sub.description
            outputs.append(
                ToolOutput(
                    schema_model,
                    name=sub.name,
                    description=description,
                )
            )
        return outputs

    def ontology_graph(
        self, context: BaseContext = BaseContext(), settings: Settings = Settings()
    ) -> JSONLDGraph:
        """Generate a union ontology graph with imports for sub-ontologies."""
        if self.metadata is None:
            raise ValueError("Collection metadata is required to build ontology graph")

        graph_items: list[Any] = []
        imports: list[Relation] = []

        for sub in self._sub_ontologies:
            if not sub.active:
                continue
            if sub.ontology.metadata is None:
                raise ValueError(
                    f"Sub-ontology '{sub.name}' metadata is required for OWL imports"
                )

            sub_graph = sub.ontology.ontology_graph(context=context, settings=settings)
            graph_items.extend(sub_graph.graph)
            imports.append(Relation(id=sub.ontology.metadata.id))

        collection_metadata = self.metadata.model_copy(update={"imports": imports})
        graph_items.append(collection_metadata)

        self._check_for_duplicate_ids(graph_items)

        return JSONLDGraph(context=context, graph=graph_items)
