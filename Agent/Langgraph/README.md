# OtariFlow

Cost-aware prompt routing with safety filtering, complexity analysis, budget control, cache hits, and an analytics dashboard.

## Run

```bash
python run.py
```

## Structure

- `backend/` contains the service, router, budget, security, logger, and server entrypoint.
- `graph/` contains the state, nodes, and workflow wrapper.
- `database/` contains the database API wrappers and model definitions.
- `cache/` contains semantic cache lookup helpers.
- `frontend/` contains the dashboard assets.
