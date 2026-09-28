"""本人が決める行動。AIの提案を自動的な約束にしない。"""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

ActionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class ActionFields(BaseModel):
    title: ActionText
    successCriteria: ActionText
    dueDate: date | None = None


class ActionCreate(ActionFields):
    candidateId: int | None = Field(default=None, gt=0)


class ActionUpdate(ActionFields):
    revision: int = Field(ge=1)
    status: Literal["planned", "in_progress", "completed", "cancelled"]
    reflection: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] = ""

    @model_validator(mode="after")
    def completed_requires_reflection(self) -> "ActionUpdate":
        if self.status == "completed" and not self.reflection:
            raise ValueError("reflection is required to complete an action")
        return self
