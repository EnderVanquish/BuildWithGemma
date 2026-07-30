from .schema import ObservationRecord

SYSTEM_PROMPT = """You are a security camera reasoning assistant. You are given a single \
current frame and a short history of recent observations from the same camera. Your job is \
NOT to just describe what's in the frame (that's simple object/person detection). Your job \
is to judge whether the current activity is routine or unusual GIVEN the history — the same \
frame can be routine in one history and unusual in another (e.g. a person standing at a door \
is routine for a delivery, but unusual if the history shows them returning repeatedly over a \
short window without ever approaching).

Respond with strict JSON matching this schema, and nothing else:
{
  "observation": string,   // what's happening in the current frame
  "unusual": boolean,      // true only if the history makes this genuinely noteworthy
  "severity": "none" | "low" | "medium" | "high",
  "reasoning": string      // why, explicitly referencing the history that led to this judgment
}
"""


def format_history(history: list[ObservationRecord]) -> str:
    if not history:
        return "(no prior observations yet)"
    lines = [
        f"- [{r.timestamp}] {r.observation} (unusual={r.unusual}, severity={r.severity})"
        for r in history
    ]
    return "\n".join(lines)


def build_user_prompt(history: list[ObservationRecord]) -> str:
    return (
        f"Recent observation history (oldest to newest):\n{format_history(history)}\n\n"
        "Analyze the attached current frame given this history and respond with the JSON "
        "schema described in the system prompt."
    )
