from __future__ import annotations

from dataclasses import dataclass

from . import store


@dataclass
class BudgetStatus:
    total: float
    spent: float
    remaining: float
    pct_spent: float
    warning: bool
    exhausted: bool


def _wrap(data: dict) -> BudgetStatus:
    return BudgetStatus(
        total=float(data["total"]),
        spent=float(data["spent"]),
        remaining=float(data["remaining"]),
        pct_spent=float(data.get("pct_spent", 0.0)),
        warning=bool(data.get("warning", False)),
        exhausted=bool(data.get("exhausted", False)),
    )


def get_status() -> BudgetStatus:
    return _wrap(store.get_budget())


def deduct(amount: float) -> BudgetStatus:
    """Synchronously deduct *amount* from the budget and return updated status."""
    return _wrap(store.deduct_budget(amount))


def reset(new_total: float) -> BudgetStatus:
    """Reset budget to *new_total* and return updated status."""
    return _wrap(store.reset_budget(new_total))


def can_afford(estimated_cost: float) -> bool:
    return store.get_budget()["remaining"] >= estimated_cost
