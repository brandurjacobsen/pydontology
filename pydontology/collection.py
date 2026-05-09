from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

from .pydontology import Pydontology
from .settings import Settings
from .models import BaseContext

if TYPE_CHECKING:
    from pydantic_ai.output import ToolOutput


@dataclass(frozen=True)
class SubOntology:
    name: str
    description: str
    ontology: Pydontology


class PydontologyCollection:
    """Registry of sub-ontologies for ToolOutput export."""
    def __init__(self) -> None:
        self._sub_ontologies: List[SubOntology] = []

    def register(self, name: str, ontology: Pydontology, description: str) -> None:
        """Register a sub-ontology with a required description."""
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
        """Return ToolOutput objects built from each sub-ontology schema."""
        try:
            from pydantic_ai.output import ToolOutput
        except ImportError as exc:
            # Keep pydantic-ai optional; surface a helpful install hint.
            raise ImportError(
                "pydantic-ai is required for ToolOutput support. Install with: pip install pydontology[ai]"
            ) from exc

        outputs = []
        for sub in self._sub_ontologies:
            schema_model = sub.ontology.schema_graph(context=context, settings=settings)
            outputs.append(
                ToolOutput(
                    name=sub.name,
                    description=sub.description,
                    output=schema_model,
                )
            )
        return outputs
