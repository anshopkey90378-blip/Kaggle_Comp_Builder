#!/usr/bin/env bash
set -euo pipefail

python -m pytest -q
python -m local_runner --scenario open_field --turns 10 >/tmp/maze_crawler_open_field.log
python -m local_runner --scenario blocked_factory --turns 10 >/tmp/maze_crawler_blocked_factory.log
python -m local_runner --scenario narrow_corridor --turns 10 >/tmp/maze_crawler_narrow_corridor.log

echo "All local Maze Crawler checks passed."
echo "Logs written to:"
echo "  /tmp/maze_crawler_open_field.log"
echo "  /tmp/maze_crawler_blocked_factory.log"
echo "  /tmp/maze_crawler_narrow_corridor.log"
