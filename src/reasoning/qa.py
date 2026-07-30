import ollama

from .prompts import format_history
from .schema import ObservationRecord

QA_MODEL_NAME = "gemma4:e2b"

QA_SYSTEM_PROMPT = """You are answering questions about a security camera's observation \
log. You are given the log (a list of past observations with timestamps, whether each \
was unusual, its severity, and the reasoning behind it) and a question about it. Answer \
using only what's in the log — if the log doesn't contain enough information to answer, \
say so rather than guessing."""


def ask_about_history(question: str, history: list[ObservationRecord]) -> str:
    response = ollama.chat(
        model=QA_MODEL_NAME,
        messages=[
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {"role": "user", "content": f"Log:\n{format_history(history)}\n\nQuestion: {question}"},
        ],
    )
    return response["message"]["content"]
