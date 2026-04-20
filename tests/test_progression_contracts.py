import pytest
from pydantic import ValidationError

from learning_core.contracts.progression import ProgressionArtifact


def test_progression_artifact_rejects_duplicate_skill_refs_across_phases():
    with pytest.raises(ValidationError, match="duplicate skillRef"):
        ProgressionArtifact.model_validate(
            {
                "phases": [
                    {"title": "Phase 1", "description": "desc", "skillRefs": ["skill:a", "skill:b"]},
                    {"title": "Phase 2", "description": "desc", "skillRefs": ["skill:b", "skill:c"]},
                ],
                "edges": [],
            }
        )


def test_progression_artifact_rejects_self_loop_edge():
    with pytest.raises(ValidationError, match="self-loop"):
        ProgressionArtifact.model_validate(
            {
                "phases": [
                    {"title": "Phase 1", "description": "desc", "skillRefs": ["skill:a"]},
                ],
                "edges": [
                    {
                        "fromSkillRef": "skill:a",
                        "toSkillRef": "skill:a",
                        "kind": "hardPrerequisite",
                    }
                ],
            }
        )


def test_progression_artifact_rejects_duplicate_edges():
    with pytest.raises(ValidationError, match="duplicate edge"):
        ProgressionArtifact.model_validate(
            {
                "phases": [
                    {"title": "Phase 1", "description": "desc", "skillRefs": ["skill:a", "skill:b"]},
                ],
                "edges": [
                    {
                        "fromSkillRef": "skill:a",
                        "toSkillRef": "skill:b",
                        "kind": "hardPrerequisite",
                    },
                    {
                        "fromSkillRef": "skill:a",
                        "toSkillRef": "skill:b",
                        "kind": "hardPrerequisite",
                    },
                ],
            }
        )


def test_progression_artifact_rejects_hard_prerequisite_cycle():
    with pytest.raises(ValidationError, match="acyclic"):
        ProgressionArtifact.model_validate(
            {
                "phases": [
                    {"title": "Phase 1", "description": "desc", "skillRefs": ["skill:a"]},
                    {"title": "Phase 2", "description": "desc", "skillRefs": ["skill:b"]},
                    {"title": "Phase 3", "description": "desc", "skillRefs": ["skill:c"]},
                ],
                "edges": [
                    {"fromSkillRef": "skill:a", "toSkillRef": "skill:b", "kind": "hardPrerequisite"},
                    {"fromSkillRef": "skill:b", "toSkillRef": "skill:c", "kind": "hardPrerequisite"},
                    {"fromSkillRef": "skill:c", "toSkillRef": "skill:a", "kind": "hardPrerequisite"},
                ],
            }
        )
