from backend.service import process_prompt


def run(prompt: str, session_id: str = "default"):
    return process_prompt(prompt, session_id=session_id)
