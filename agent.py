"""Baseline Maze Crawler Kaggle agent.

This module intentionally avoids depending on a private competition package so it can
be imported and smoke-tested locally.  The public Kaggle entry point is ``agent``.
The strategy is conservative: protect the factory, remember observed map cells,
and reserve intended destinations so friendly units do not pick the same tile.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

Position = tuple[int, int]

DIRECTIONS: dict[str, Position] = {
    "N": (0, 1),
    "E": (1, 0),
    "W": (-1, 0),
    "S": (0, -1),
    "WAIT": (0, 0),
}
MOVE_PRIORITY = ("N", "E", "W", "S", "WAIT")
FACTORY_TYPES = {"factory", "base", "hq"}
BLOCKED_TERRAIN = {"wall", "blocked", "rock", "obstacle"}
RESOURCE_TERRAIN = {"crystal", "energy", "mine", "resource"}


@dataclass(slots=True)
class Unit:
    """Normalized unit representation extracted from a Kaggle observation."""

    unit_id: str
    unit_type: str
    position: Position
    cargo: int = 0

    @property
    def is_factory(self) -> bool:
        return self.unit_type.lower() in FACTORY_TYPES


@dataclass(slots=True)
class CellMemory:
    """Remembered facts for a single map coordinate."""

    terrain: str = "unknown"
    last_seen: int = 0
    resource: str | None = None
    occupied_by: str | None = None

    @property
    def blocked(self) -> bool:
        return self.terrain.lower() in BLOCKED_TERRAIN


@dataclass
class WorldMemory:
    """Persistent fog-of-war memory shared across calls to ``agent``."""

    cells: dict[Position, CellMemory] = field(default_factory=dict)
    turn: int = 0
    scroll_y: int | None = None

    def update(self, observation: Mapping[str, Any]) -> None:
        self.turn = int(observation.get("step", observation.get("turn", self.turn + 1)) or 0)
        self.scroll_y = _first_int(observation, ("scroll_y", "south_boundary", "floor_y"), self.scroll_y)
        for cell in _iter_observed_cells(observation):
            pos = cell[0]
            terrain = cell[1]
            resource = cell[2]
            memory = self.cells.setdefault(pos, CellMemory())
            memory.terrain = terrain or memory.terrain
            memory.resource = resource
            memory.last_seen = self.turn
            memory.occupied_by = None
        for unit in parse_units(observation):
            memory = self.cells.setdefault(unit.position, CellMemory(last_seen=self.turn))
            memory.last_seen = self.turn
            memory.occupied_by = unit.unit_id

    def is_blocked(self, position: Position) -> bool:
        return self.cells.get(position, CellMemory()).blocked

    def is_safe(self, position: Position) -> bool:
        if self.scroll_y is not None and position[1] <= self.scroll_y:
            return False
        return not self.is_blocked(position)

    def resource_age(self, position: Position) -> int | None:
        cell = self.cells.get(position)
        if not cell or not cell.resource:
            return None
        return self.turn - cell.last_seen

    def turns_until_scroll_death(self, position: Position, scroll_speed: int = 1) -> int | None:
        if self.scroll_y is None:
            return None
        return max(0, (position[1] - self.scroll_y) // max(1, scroll_speed))


class ReservationTable:
    """Tracks cells already claimed for this turn."""

    def __init__(self) -> None:
        self._reserved: dict[Position, str] = {}

    def reserve(self, unit_id: str, position: Position) -> bool:
        owner = self._reserved.get(position)
        if owner is not None and owner != unit_id:
            return False
        self._reserved[position] = unit_id
        return True

    def is_reserved(self, position: Position) -> bool:
        return position in self._reserved


def agent(observation: Mapping[str, Any], configuration: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Kaggle-compatible entry point.

    The returned action schema is intentionally simple and JSON-serializable:
    ``{unit_id: {"type": "move", "direction": "N"}}``.  If the official
    environment requires a different wrapper, only ``format_move`` should need to
    change.
    """

    del configuration
    if not isinstance(observation, Mapping):
        return {}

    memory = _get_memory()
    memory.update(observation)
    units = parse_units(observation)
    reservations = ReservationTable()
    actions: dict[str, Any] = {}

    for unit in sorted(units, key=_unit_priority):
        direction = choose_direction(unit, memory, reservations)
        destination = add_pos(unit.position, DIRECTIONS[direction])
        reservations.reserve(unit.unit_id, destination)
        actions[unit.unit_id] = format_move(direction)

    return actions


def choose_direction(unit: Unit, memory: WorldMemory, reservations: ReservationTable) -> str:
    """Choose a conservative legal-looking movement direction for one unit."""

    for direction in preferred_directions(unit):
        destination = add_pos(unit.position, DIRECTIONS[direction])
        if memory.is_safe(destination) and not reservations.is_reserved(destination):
            return direction
    return "WAIT"


def preferred_directions(unit: Unit) -> Iterable[str]:
    """Factory always prefers north; other units avoid blocking by using same base order."""

    if unit.is_factory:
        return MOVE_PRIORITY
    if unit.cargo > 0:
        return ("N", "W", "E", "S", "WAIT")
    return MOVE_PRIORITY


def find_path(start: Position, goal: Position, memory: WorldMemory, max_nodes: int = 512) -> list[Position]:
    """Small BFS pathfinder over remembered safe cells for future strategy modules."""

    if start == goal:
        return [start]
    queue: deque[Position] = deque([start])
    parent: dict[Position, Position | None] = {start: None}
    while queue and len(parent) < max_nodes:
        current = queue.popleft()
        for delta in (DIRECTIONS["N"], DIRECTIONS["E"], DIRECTIONS["W"], DIRECTIONS["S"]):
            nxt = add_pos(current, delta)
            if nxt in parent or not memory.is_safe(nxt):
                continue
            parent[nxt] = current
            if nxt == goal:
                return _reconstruct_path(parent, goal)
            queue.append(nxt)
    return []


def parse_units(observation: Mapping[str, Any]) -> list[Unit]:
    """Extract units from common observation shapes without throwing."""

    raw_units = observation.get("units", observation.get("my_units", []))
    if isinstance(raw_units, Mapping):
        iterable = [dict(value, id=key) if isinstance(value, Mapping) else {"id": key} for key, value in raw_units.items()]
    elif isinstance(raw_units, list):
        iterable = raw_units
    else:
        iterable = []

    units: list[Unit] = []
    for index, raw in enumerate(iterable):
        if not isinstance(raw, Mapping):
            continue
        pos = _position_from(raw)
        if pos is None:
            continue
        unit_id = str(raw.get("id", raw.get("unit_id", f"unit_{index}")))
        unit_type = str(raw.get("type", raw.get("unit_type", "unit")))
        cargo = int(raw.get("cargo", raw.get("energy", 0)) or 0)
        units.append(Unit(unit_id=unit_id, unit_type=unit_type, position=pos, cargo=cargo))
    return units


def format_move(direction: str) -> dict[str, str]:
    return {"type": "move", "direction": direction}


def reset_memory() -> None:
    """Reset global memory for tests or new local matches."""

    global _MEMORY
    _MEMORY = WorldMemory()


def _get_memory() -> WorldMemory:
    global _MEMORY
    try:
        return _MEMORY
    except NameError:
        _MEMORY = WorldMemory()
        return _MEMORY


def _unit_priority(unit: Unit) -> tuple[int, str]:
    return (0 if unit.is_factory else 1, unit.unit_id)


def _iter_observed_cells(observation: Mapping[str, Any]) -> Iterable[tuple[Position, str, str | None]]:
    cells = observation.get("cells", observation.get("map", []))
    if isinstance(cells, Mapping):
        for key, value in cells.items():
            pos = _position_from_key(key)
            if pos is None:
                continue
            terrain = str(value.get("terrain", value.get("type", "unknown"))) if isinstance(value, Mapping) else str(value)
            resource = _resource_from(value)
            yield pos, terrain, resource
    elif isinstance(cells, list):
        for raw in cells:
            if not isinstance(raw, Mapping):
                continue
            pos = _position_from(raw)
            if pos is None:
                continue
            terrain = str(raw.get("terrain", raw.get("type", "unknown")))
            resource = _resource_from(raw)
            yield pos, terrain, resource


def _position_from(raw: Mapping[str, Any]) -> Position | None:
    if "position" in raw and isinstance(raw["position"], (list, tuple)) and len(raw["position"]) >= 2:
        return int(raw["position"][0]), int(raw["position"][1])
    if "pos" in raw and isinstance(raw["pos"], (list, tuple)) and len(raw["pos"]) >= 2:
        return int(raw["pos"][0]), int(raw["pos"][1])
    if "x" in raw and "y" in raw:
        return int(raw["x"]), int(raw["y"])
    return None


def _position_from_key(key: Any) -> Position | None:
    if isinstance(key, tuple) and len(key) == 2:
        return int(key[0]), int(key[1])
    if isinstance(key, str):
        parts = key.replace(",", " ").split()
        if len(parts) == 2 and all(part.lstrip("-").isdigit() for part in parts):
            return int(parts[0]), int(parts[1])
    return None


def _resource_from(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return str(value) if str(value).lower() in RESOURCE_TERRAIN else None
    resource = value.get("resource") or value.get("resource_type")
    terrain = value.get("terrain", value.get("type"))
    if resource:
        return str(resource)
    if terrain and str(terrain).lower() in RESOURCE_TERRAIN:
        return str(terrain)
    return None


def _first_int(observation: Mapping[str, Any], keys: Iterable[str], default: int | None) -> int | None:
    for key in keys:
        if key in observation and observation[key] is not None:
            return int(observation[key])
    return default


def add_pos(left: Position, right: Position) -> Position:
    return left[0] + right[0], left[1] + right[1]


def _reconstruct_path(parent: Mapping[Position, Position | None], goal: Position) -> list[Position]:
    path = [goal]
    current = goal
    while parent[current] is not None:
        current = parent[current]  # type: ignore[index]
        path.append(current)
    path.reverse()
    return path
