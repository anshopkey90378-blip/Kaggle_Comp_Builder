# Kaggle_Comp_Builder

## Maze Crawler Competition Plan

Maze Crawler is a 1v1 Kaggle Simulation/AI Bot competition where the submission is an autonomous agent, not a static machine-learning model. The immediate goal is to build a reliable bot that survives the scrolling maze, avoids self-blocking, and wins consistently through better movement, pathing, resource handling, and factory safety.

### 1. First Milestone: Build a Valid Baseline Agent

The first priority is not leaderboard strength; it is a submission that never crashes, never times out, and can complete Kaggle self-play validation.

Key work:

- Create the minimum agent entry point expected by Kaggle.
- Parse each turn observation safely.
- Return legal actions for every controllable unit.
- Add defensive fallbacks so unknown or malformed observations do not throw exceptions.
- Prefer simple northward factory movement when no tactical choice is available.

Success criteria:

- The agent passes local smoke tests.
- The agent can run against itself without exceptions.
- Every unit gets either a legal action or an explicit no-op.

### 2. Map Memory and Fog-of-War Foundation

Because the game has fog of war, the bot needs persistent memory. This should be implemented before advanced strategy because every later system depends on remembered walls, cleared paths, crystals, mines, enemy positions, and danger zones.

Key work:

- Maintain a turn-by-turn world model keyed by map coordinates.
- Store observed terrain, walls, resources, units, and factory positions.
- Decay or mark stale information instead of deleting it immediately.
- Track the advancing southern boundary as a lethal deadline for every coordinate.
- Expose helper queries such as `is_blocked`, `is_safe`, `resource_age`, and `turns_until_scroll_death`.

Success criteria:

- The bot remembers walls and resources after they leave vision.
- Pathing can query both visible and remembered cells.
- The factory never intentionally moves into a known lethal or blocked tile.

### 3. Reservation and Pathing System

The most important strategic system is reservation-based movement. The factory and robots must not all greedily choose cells independently, because they can trap each other in narrow maze corridors.

Key work:

- Implement pathfinding over remembered terrain, starting with BFS or A*.
- Reserve current and intended future cells for high-priority units.
- Give the factory first priority, workers second, resource carriers third, scouts/miners later.
- Prevent lower-priority units from stepping into the factory corridor.
- Add simple congestion rules: wait, step aside, or reroute if a unit would block the factory.

Success criteria:

- No two friendly units intentionally target the same tile.
- Workers and scouts avoid occupying the factory's next required path.
- The factory has a reserved northward escape route whenever possible.

### 4. Factory Survival Policy

The factory is the only unit that matters for win/loss, so all decisions should be evaluated by whether they preserve factory momentum and avoid the scrolling floor.

Key work:

- Score factory moves by northward progress, safety margin from the scroll, and path openness.
- Avoid building when the factory must move to survive.
- Detect when a wall blocks the factory and assign workers to clear it.
- Prefer survival over resource collection.
- Handle opponent collision rules conservatively when enemy factory information is known.

Success criteria:

- Factory movement remains north-biased.
- The factory does not pause for economy if the scroll margin is low.
- Wall clearing supports the factory path rather than random exploration.

### 5. Economy and Unit Roles

After survival and pathing are stable, add a controlled economy. The economy should be useful without creating traffic that kills the factory.

Key work:

- Workers: assign to walls that block or shorten the factory route.
- Scouts/couriers: collect reachable crystals and return energy to the factory.
- Miners: only build when the factory has enough scroll margin and a known mine is safe long enough to repay investment.
- Use a resource task board so multiple units do not chase the same crystal unnecessarily.
- Always account for return trips before valuing carried energy.

Success criteria:

- Resource collection improves survival options without causing jams.
- Scouts return carried energy before the scroll makes the route unsafe.
- Miners are treated as situational long-term investments, not automatic purchases.

### 6. Local Testing Harness

A strong iteration loop is essential because Kaggle submissions are limited and the active ladder only keeps the latest two submissions.

Key work:

- Add a deterministic local runner if the Kaggle environment package exposes one.
- Store validation logs and replay seeds.
- Add smoke tests for observation parsing, action legality, pathfinding, reservations, and emergency movement.
- Build scenario fixtures for narrow corridors, blocked factory paths, crystals behind side passages, and scroll pressure.

Success criteria:

- Most bugs are caught before Kaggle submission.
- Each strategy change can be tested in repeatable scenarios.
- Failed Kaggle logs can be replayed locally or converted into fixtures.

### 7. Submission Strategy

Since only five agents can be submitted per day and only the latest two stay active, submissions should be treated as scarce experiments.

Key work:

- Keep one stable submission slot and one experimental slot.
- Submit only after local validation passes.
- Record each submission's commit hash, strategy changes, validation result, and leaderboard trend.
- Avoid replacing both active slots with unproven experiments.

Success criteria:

- Every submission has a clear hypothesis.
- Regressions are traceable to a specific commit.
- At least one robust bot remains active while experiments continue.

## Immediate Next Steps

1. Confirm the official Kaggle environment API: observation schema, action schema, unit names, legal moves, and package entry point.
2. Scaffold the baseline agent and local smoke-test runner.
3. Implement world memory and factory-first movement.
4. Add reservation-based movement before adding aggressive resource collection.
5. Iterate with local scenarios, then use Kaggle submissions sparingly for validation and rating feedback.
