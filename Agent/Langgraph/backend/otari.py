from __future__ import annotations

from .service import process_prompt


def generate(prompt: str, session_id: str = "default"):
    return process_prompt(prompt, session_id=session_id)
