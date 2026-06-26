"""Tiny local smoke runner for the Maze Crawler baseline agent.

This is not a full recreation of the Kaggle environment.  It is a deterministic
sanity harness that repeatedly calls ``agent.agent`` with simple observations so
we can catch crashes, memory regressions, and obvious movement/reservation bugs
before spending Kaggle submissions.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Any

from agent import DIRECTIONS, agent, reset_memory


@dataclass(slots=True)
class RunnerUnit:
    unit_id: str
    unit_type: str
    x: int
    y: int
    cargo: int = 0

    def as_observation(self) -> dict[str, Any]:
        return {
            "id": self.unit_id,
            "type": self.unit_type,
            "x": self.x,
            "y": self.y,
            "cargo": self.cargo,
        }


@dataclass
class Scenario:
    """A deterministic local scenario made from visible cells and friendly units."""

    name: str
    units: list[RunnerUnit]
    walls: set[tuple[int, int]] = field(default_factory=set)
    resources: set[tuple[int, int]] = field(default_factory=set)
    floor_radius: int = 3
    south_boundary: int = -10
    scroll_every: int = 5

    def observation(self, turn: int) -> dict[str, Any]:
        factory = next((unit for unit in self.units if unit.unit_type == "factory"), self.units[0])
        cells: list[dict[str, Any]] = []
        for x in range(factory.x - self.floor_radius, factory.x + self.floor_radius + 1):
            for y in range(factory.y - 1, factory.y + self.floor_radius + 1):
                terrain = "floor"
                if (x, y) in self.walls:
                    terrain = "wall"
                elif (x, y) in self.resources:
                    terrain = "crystal"
                cells.append({"x": x, "y": y, "terrain": terrain})
        return {
            "turn": turn,
            "south_boundary": self.south_boundary + turn // self.scroll_every,
            "units": [unit.as_observation() for unit in self.units],
            "cells": cells,
        }

    def apply_actions(self, actions: dict[str, Any]) -> None:
        occupied = {(unit.x, unit.y): unit.unit_id for unit in self.units}
        for unit in self.units:
            action = actions.get(unit.unit_id, {})
            direction = action.get("direction", "WAIT") if isinstance(action, dict) else "WAIT"
            dx, dy = DIRECTIONS.get(direction, DIRECTIONS["WAIT"])
            destination = (unit.x + dx, unit.y + dy)
            if destination in self.walls or occupied.get(destination) not in (None, unit.unit_id):
                continue
            occupied.pop((unit.x, unit.y), None)
            unit.x, unit.y = destination
            occupied[destination] = unit.unit_id


def build_scenario(name: str) -> Scenario:
    """Create one of the built-in smoke-test scenarios."""

    if name == "blocked_factory":
        return Scenario(
            name=name,
            units=[RunnerUnit("factory", "factory", 0, 0), RunnerUnit("worker_1", "worker", 1, 0)],
            walls={(0, 1), (0, 2)},
            resources={(2, 2)},
        )
    if name == "narrow_corridor":
        walls = {(x, y) for x in range(-2, 3) for y in range(0, 8) if x not in (0,)}
        return Scenario(
            name=name,
            units=[RunnerUnit("factory", "factory", 0, 0), RunnerUnit("scout_1", "scout", 0, 2)],
            walls=walls,
            resources={(0, 6)},
            floor_radius=2,
        )
    return Scenario(
        name="open_field",
        units=[RunnerUnit("factory", "factory", 0, 0), RunnerUnit("scout_1", "scout", 1, 0)],
        resources={(1, 3), (-1, 4)},
    )


def run_scenario(name: str, turns: int) -> list[dict[str, Any]]:
    """Run a built-in scenario and return per-turn action logs."""

    reset_memory()
    scenario = build_scenario(name)
    logs: list[dict[str, Any]] = []
    for turn in range(1, turns + 1):
        observation = scenario.observation(turn)
        actions = agent(observation)
        scenario.apply_actions(actions)
        logs.append({"turn": turn, "actions": actions, "units": [unit.as_observation() for unit in scenario.units]})
    return logs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic local Maze Crawler smoke scenario.")
    parser.add_argument("--scenario", default="open_field", choices=("open_field", "blocked_factory", "narrow_corridor"))
    parser.add_argument("--turns", type=int, default=10)
    args = parser.parse_args()

    for entry in run_scenario(args.scenario, args.turns):
        print(entry)


if __name__ == "__main__":
    main()
