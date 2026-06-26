# Maze Crawler Test Guide

This guide explains how to test the current Maze Crawler bot before using a Kaggle submission. The goal is to catch crashes, illegal-looking movement choices, wall-collision mistakes, and self-blocking regressions locally.

## 1. Install Test Dependencies

From the repository root, install the development dependency file if `pytest` is not already available:

```bash
python -m pip install -r requirements-dev.txt
```

## 2. Run the Unit Test Suite

Run the main automated checks:

```bash
pytest -q
```

What this currently verifies:

- The factory prefers moving north when the north tile is safe.
- The factory does not intentionally move north into a remembered wall.
- The reservation table rejects duplicate destination claims from different units.
- The parser accepts both list-shaped and mapping-shaped unit observations.
- The BFS helper routes around remembered walls.
- The local runner can execute repeated turns without crashing.
- The narrow-corridor smoke scenario keeps units in unique positions.

## 3. Run Scenario Smoke Tests Manually

The local runner is not a full Kaggle environment. It is a deterministic safety harness that repeatedly calls `agent.agent` using small handcrafted observations.

### Open Field

```bash
python -m local_runner --scenario open_field --turns 10
```

Use this to confirm the agent can move through repeated low-pressure turns.

### Blocked Factory

```bash
python -m local_runner --scenario blocked_factory --turns 10
```

Use this to confirm the factory does not knowingly walk into a wall directly north of it.

### Narrow Corridor

```bash
python -m local_runner --scenario narrow_corridor --turns 10
```

Use this to inspect simple self-blocking behavior when the factory and a scout share a constrained lane.

## 4. Run Every Local Check With One Command

Use the helper script when you want the full local safety pass:

```bash
./scripts/test_all.sh
```

The script runs `pytest` plus all three local scenarios. Scenario logs are written to `/tmp` so they do not dirty the git working tree.

## 5. Interpreting Failures

If `pytest -q` fails, fix that before running scenario tests. Unit tests are smaller and usually identify the exact broken helper or behavior.

If a local scenario fails or prints suspicious actions:

1. Re-run that single scenario with fewer turns.
2. Check the per-turn `actions` and `units` output.
3. Add a regression test in `tests/test_local_runner.py` or `tests/test_agent.py` before changing strategy logic.
4. Confirm `./scripts/test_all.sh` passes before attempting a Kaggle validation submission.

## 6. Before Kaggle Submission

Before spending a Kaggle daily submission, run:

```bash
./scripts/test_all.sh
```

Then confirm the official competition action schema. If Kaggle expects a different action format, update `format_move` in `agent.py` and add a test for the new schema before submitting.

## 7. Next Testing Targets

The next implementation phase should add tests for:

- Worker wall-clearing actions when the factory path is blocked.
- Scout crystal pickup and return-to-factory behavior.
- Scroll pressure emergencies where the factory must move instead of building or waiting.
- Memory persistence when a wall or resource leaves the visible observation window.
