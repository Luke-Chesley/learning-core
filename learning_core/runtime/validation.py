from __future__ import annotations

from pydantic import BaseModel

from learning_core.runtime.errors import ContractValidationError


def validate_structured_artifact(output_model: type[BaseModel], raw_artifact: object) -> BaseModel:
    try:
        return output_model.model_validate(raw_artifact)
    except Exception as error:
        raise ContractValidationError(str(error)) from error
