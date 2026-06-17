from datetime import datetime
from pydantic import BaseModel

class RemediationPlanResponse(BaseModel):
    id: str
    finding_id: str
    steps: list[str]
    estimated_effort_hours: int
    priority: str
    suggested_owner_role: str
    approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class RemediationPlanUpdateRequest(BaseModel):
    steps: list[str] | None = None
    estimated_effort_hours: int | None = None
    priority: str | None = None
    suggested_owner_role: str | None = None
    approved: bool | None = None
