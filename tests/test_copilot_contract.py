import pytest
from pydantic import ValidationError

from learning_core.contracts.copilot import CopilotChatArtifact


def test_copilot_chat_artifact_accepts_bounded_actions():
    artifact = CopilotChatArtifact.model_validate(
        {
            "answer": "Thursday looks heavy. Move the fractions practice block to Friday.",
            "actions": [
                {
                    "id": "action-1",
                    "kind": "planning.adjust_day_load",
                    "label": "Move fractions practice to Friday",
                    "description": "Shift the fractions route item off the overloaded Thursday plan.",
                    "rationale": "Friday has more available minutes in the current weekly route.",
                    "confidence": "high",
                    "requiresApproval": True,
                    "target": {
                        "entityType": "weekly_route_item",
                        "entityId": "route-item-1",
                        "date": "2026-04-24",
                    },
                    "payload": {
                        "weeklyRouteId": "weekly-route-1",
                        "weeklyRouteItemId": "route-item-1",
                        "currentDate": "2026-04-23",
                        "targetDate": "2026-04-24",
                        "targetIndex": 0,
                        "reason": "Friday has more room for this lesson.",
                    },
                }
            ],
        }
    )

    assert artifact.actions[0].kind == "planning.adjust_day_load"
    assert artifact.actions[0].payload.weeklyRouteItemId == "route-item-1"


def test_copilot_chat_artifact_rejects_unsupported_action_kind():
    with pytest.raises(ValidationError):
        CopilotChatArtifact.model_validate(
            {
                "answer": "I can suggest a standards remap.",
                "actions": [
                    {
                        "id": "action-1",
                        "kind": "standards.map",
                        "label": "Map standards",
                        "description": "Unsupported action.",
                        "payload": {},
                    }
                ],
            }
        )
