from __future__ import annotations

from learning_core.packs.base import RuntimePackDefinition
from learning_core.packs.domains.homeschool.pack import build_homeschool_pack


DOMAIN_PACKS: dict[str, RuntimePackDefinition] = {
    "homeschool": build_homeschool_pack(),
}


def get_domain_pack(name: str) -> RuntimePackDefinition | None:
    return DOMAIN_PACKS.get(name)
