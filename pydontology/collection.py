from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List

from .models import BaseContext, BaseMetaData, JSONLDGraph, Relation
from .pydontology import Pydontology
from .settings import Settings

if TYPE_CHECKING:
    from pydantic_ai.output import ToolOutput


@dataclass(frozen=True)
class SubOntology:
    name: str
    description: str
    ontology: Pydontology


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
            raise ValueError(f"Duplicate @id values found in ontology graph: {duplicates}")

    def register(self, name: str, ontology: Pydontology, description: str) -> None:
        """Register a sub-ontology with a description."""

        if any(item.name == name for item in self._sub_ontologies):
            raise ValueError(f"Sub-ontology '{name}' already registered")
        self._sub_ontologies.append(
            SubOntology(name=name, description=description, ontology=ontology)
        )

    def tool_outputs(
        self,
        context: BaseContext = BaseContext(),
        settings: Settings = Settings(),
    ) -> list[ToolOutput]:
        """Return ToolOutput objects built from each sub-ontology schema.

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
            if sub.ontology.metadata is None:
                raise ValueError(
                    f"Sub-ontology '{sub.name}' metadata is required for imports"
                )

            sub_graph = sub.ontology.ontology_graph(context=context, settings=settings)
            graph_items.extend(sub_graph.graph)
            imports.append(Relation(id=sub.ontology.metadata.id))

        collection_metadata = self.metadata.model_copy(update={"imports": imports})
        graph_items.append(collection_metadata)

        self._check_for_duplicate_ids(graph_items)

        return JSONLDGraph(context=context, graph=graph_items)
