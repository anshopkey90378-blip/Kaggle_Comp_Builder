from agent import ReservationTable, WorldMemory, agent, find_path, parse_units, reset_memory


def test_agent_moves_factory_north_when_safe():
    reset_memory()
    obs = {
        "turn": 1,
        "south_boundary": -5,
        "units": [{"id": "factory", "type": "factory", "x": 0, "y": 0}],
        "cells": [{"x": 0, "y": 1, "terrain": "floor"}],
    }

    actions = agent(obs)

    assert actions["factory"] == {"type": "move", "direction": "N"}


def test_agent_avoids_known_wall():
    reset_memory()
    obs = {
        "turn": 1,
        "units": [{"id": "factory", "type": "factory", "position": [0, 0]}],
        "cells": [{"position": [0, 1], "terrain": "wall"}],
    }

    actions = agent(obs)

    assert actions["factory"]["direction"] != "N"


def test_reservations_prevent_duplicate_destinations():
    table = ReservationTable()

    assert table.reserve("a", (1, 1))
    assert not table.reserve("b", (1, 1))
    assert table.reserve("a", (1, 1))


def test_parse_units_accepts_mapping_shape():
    units = parse_units({"units": {"u1": {"type": "worker", "x": 3, "y": 4}}})

    assert len(units) == 1
    assert units[0].unit_id == "u1"
    assert units[0].position == (3, 4)


def test_find_path_uses_memory_and_avoids_walls():
    memory = WorldMemory()
    memory.update(
        {
            "turn": 1,
            "cells": [
                {"x": 0, "y": 1, "terrain": "wall"},
                {"x": 1, "y": 0, "terrain": "floor"},
                {"x": 1, "y": 1, "terrain": "floor"},
            ],
        }
    )

    path = find_path((0, 0), (1, 1), memory)

    assert path == [(0, 0), (1, 0), (1, 1)]
