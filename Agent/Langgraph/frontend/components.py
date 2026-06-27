"""Reusable front-end component placeholders for OtariFlow."""


def metric(label: str, value: str, sub: str = "") -> str:
    return f"{label}: {value} {sub}".strip()
