from __future__ import annotations

from typing import Any

from learning_core.contracts.progression import SkillCatalogItem


def build_skill_catalog_from_document(document: dict[str, Any]) -> list[SkillCatalogItem]:
    skill_catalog: list[SkillCatalogItem] = []

    def walk(node: Any, path: list[str]) -> None:
        if isinstance(node, str):
            skill_catalog.append(
                SkillCatalogItem(
                    skillRef=" / ".join(path + [node]),
                    title=node,
                    domainTitle=path[0] if len(path) > 0 else None,
                    strandTitle=path[1] if len(path) > 1 else None,
                    goalGroupTitle=path[2] if len(path) > 2 else None,
                    ordinal=len(skill_catalog) + 1,
                )
            )
            return

        if isinstance(node, list):
            for item in node:
                if isinstance(item, str):
                    walk(item, path)
            return

        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str):
                    skill_catalog.append(
                        SkillCatalogItem(
                            skillRef=" / ".join(path + [key]),
                            title=key,
                            domainTitle=path[0] if len(path) > 0 else None,
                            strandTitle=path[1] if len(path) > 1 else None,
                            goalGroupTitle=path[2] if len(path) > 2 else None,
                            ordinal=len(skill_catalog) + 1,
                        )
                    )
                else:
                    walk(value, path + [key])

    walk(document, [])
    return skill_catalog
