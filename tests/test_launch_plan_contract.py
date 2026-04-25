from __future__ import annotations

import pytest

from learning_core.contracts.launch_plan import LaunchPlanArtifact


def test_launch_plan_artifact_requires_opening_skill_refs():
    with pytest.raises(ValueError, match="openingSkillRef"):
        LaunchPlanArtifact.model_validate(
            {
                "chosenHorizon": "one_week",
                "scopeSummary": "Start with the first cluster of skills.",
                "initialSliceUsed": True,
                "initialSliceLabel": "Start here",
                "openingSkillRefs": [],
            }
        )


def test_launch_plan_artifact_rejects_model_authored_opening_unit_refs():
    with pytest.raises(ValueError, match="openingUnitRefs"):
        LaunchPlanArtifact.model_validate(
            {
                "chosenHorizon": "one_week",
                "scopeSummary": "Start with the first cluster of skills.",
                "initialSliceUsed": True,
                "initialSliceLabel": "Start here",
                "openingSkillRefs": ["skill:fractions/intro/recognize-halves"],
                "openingUnitRefs": ["unit:1:intro"],
            }
        )
