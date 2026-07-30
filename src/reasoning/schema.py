from typing import Literal

from pydantic import BaseModel, model_validator

Severity = Literal["none", "low", "medium", "high"]


class ObservationRecord(BaseModel):
    timestamp: str
    observation: str
    unusual: bool
    severity: Severity
    reasoning: str

    @model_validator(mode="after")
    def _reconcile_verdict(self) -> "ObservationRecord":
        """Keeps `unusual` and `severity` from contradicting each other.

        The model does emit contradictions (observed: unusual=False with severity="low"),
        which reads as incoherent on a dashboard where both are shown side by side. Rather
        than drop the record, trust whichever field indicates *more* concern — under-
        reporting a real event is the worse failure for a security tool.
        """
        if self.severity != "none" and not self.unusual:
            object.__setattr__(self, "unusual", True)
        elif self.unusual and self.severity == "none":
            object.__setattr__(self, "severity", "low")
        return self
