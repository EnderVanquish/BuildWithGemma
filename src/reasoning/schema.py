from typing import Literal

from pydantic import BaseModel

Severity = Literal["none", "low", "medium", "high"]


class ObservationRecord(BaseModel):
    timestamp: str
    observation: str
    unusual: bool
    severity: Severity
    reasoning: str
