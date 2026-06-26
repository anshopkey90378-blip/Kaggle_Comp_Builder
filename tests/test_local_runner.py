from local_runner import build_scenario, run_scenario


def test_local_runner_open_field_completes_multiple_turns():
    logs = run_scenario("open_field", 5)

    assert len(logs) == 5
    assert all("factory" in entry["actions"] for entry in logs)


def test_local_runner_blocked_factory_does_not_walk_into_wall():
    scenario = build_scenario("blocked_factory")
    observation = scenario.observation(1)

    assert {"x": 0, "y": 1, "terrain": "wall"} in observation["cells"]

    logs = run_scenario("blocked_factory", 1)

    assert logs[0]["actions"]["factory"]["direction"] != "N"


def test_local_runner_narrow_corridor_keeps_unique_positions():
    logs = run_scenario("narrow_corridor", 3)

    for entry in logs:
        positions = {(unit["x"], unit["y"]) for unit in entry["units"]}
        assert len(positions) == len(entry["units"])
