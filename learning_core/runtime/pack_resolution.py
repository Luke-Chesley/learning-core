from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from learning_core.packs.base import RuntimePackDefinition
from learning_core.packs.registry import get_domain_pack
from learning_core.runtime.request_normalization import RuntimeRequest


@dataclass(frozen=True)
class ResolvedRuntimePack:
    name: str
    category: str
    prompt_sections: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def _from_runtime_pack(pack: RuntimePackDefinition, *, source: str) -> ResolvedRuntimePack:
    metadata = dict(pack.metadata)
    metadata["source"] = source
    return ResolvedRuntimePack(
        name=pack.name,
        category=pack.category,
        prompt_sections=pack.prompt_sections,
        metadata=metadata,
    )


def resolve_runtime_packs(runtime_request: RuntimeRequest) -> list[ResolvedRuntimePack]:
    resolved: list[ResolvedRuntimePack] = []
    seen: set[str] = set()

    if runtime_request.template:
        domain_pack = get_domain_pack(runtime_request.template)
        if domain_pack is not None:
            resolved.append(_from_runtime_pack(domain_pack, source="template"))
            seen.add(domain_pack.name)

    if runtime_request.operation_name == "activity_generate":
        from learning_core.skills.activity_generate.scripts.main import _PACKS_BY_NAME, _select_packs

        selection = _select_packs(runtime_request.payload)
        for pack_name in selection.included_packs:
            if pack_name in seen:
                continue
            legacy_pack = _PACKS_BY_NAME[pack_name]
            resolved.append(
                ResolvedRuntimePack(
                    name=pack_name,
                    category="subject",
                    prompt_sections=tuple(legacy_pack.prompt_sections()),
                    metadata={
                        "source": "activity_subject_inference",
                        "selection_reason": selection.pack_selection_reason.get(pack_name, []),
                    },
                )
            )
            seen.add(pack_name)

    for hint in runtime_request.pack_hints:
        if hint in seen:
            continue
        domain_pack = get_domain_pack(hint)
        if domain_pack is not None:
            resolved.append(_from_runtime_pack(domain_pack, source="pack_hint"))
            seen.add(domain_pack.name)

    return resolved
