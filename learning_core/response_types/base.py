from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel


ArtifactFactory = Callable[[str], BaseModel]


@dataclass(frozen=True)
class ResponseTypeDefinition:
    name: str
    artifact_model: type[BaseModel]
    response_mode: str = "structured"
    artifact_factory: ArtifactFactory | None = None
    description: str | None = None

    def build_text_artifact(self, raw_text: str) -> BaseModel:
        if self.artifact_factory is None:
            raise ValueError(f"Response type '{self.name}' does not support text finalization.")
        return self.artifact_factory(raw_text)
