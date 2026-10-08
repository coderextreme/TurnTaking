"""
CLI and Bridge utility for TurnProg execution, test running, and interactive web visualization.
"""

import sys
import json
import time
import zipfile
import io
import os
import unittest
from unittest.runner import TextTestResult

from turnprog.models import (
    GameState,
    Move,
    Player,
    PowerPlay,
    PowerPlayType,
    ProgressionType,
    BufferState,
)
from turnprog.progression import (
    PredefinedProgression,
    VariableProgression,
    RoundOrderProgression,
    SnatchProgression,
    LimitedProgression,
    ContinuousProgression,
)
from turnprog.game_master import GameMaster
from turnprog.cluster import ClusterCoordinator, NodeRole
from turnprog.scenarios import (
    run_predefined_scenario,
    run_variable_scenario,
    run_round_order_scenario,
    run_snatch_scenario,
    run_cluster_failover_scenario,
)


def run_scenario(name: str):
    mapping = {
        "predefined": run_predefined_scenario,
        "variable": run_variable_scenario,
        "round_order": run_round_order_scenario,
        "snatch": run_snatch_scenario,
        "cluster_failover": run_cluster_failover_scenario,
    }
    fn = mapping.get(name)
    if not fn:
        return {"error": f"Unknown scenario: {name}"}
    return fn()


def run_tests():
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir="tests", pattern="test_*.py")
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    duration = time.time() - start_time

    return {
        "total_tests": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "was_successful": result.wasSuccessful(),
        "duration_sec": round(duration, 4),
        "raw_output": stream.getvalue(),
        "failure_details": [str(f[1]) for f in result.failures],
        "error_details": [str(e[1]) for e in result.errors],
    }


def create_zip_archive():
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("."):
            if "node_modules" in root or ".git" in root or "__pycache__" in root or "dist" in root:
                continue
            for f in files:
                if f.endswith((".py", ".md", ".toml", ".html", ".css", ".ts", ".tsx", ".json")):
                    filepath = os.path.join(root, f)
                    arcname = os.path.relpath(filepath, ".")
                    zf.write(filepath, arcname)
    return zip_buffer.getvalue()


def main():
    # Redirect logging to stderr or silence during CLI execution
    import logging
    logging.basicConfig(level=logging.ERROR)

    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command specified"}))
        return

    cmd = sys.argv[1]
    if cmd == "scenario":
        sc_name = sys.argv[2] if len(sys.argv) > 2 else "predefined"
        res = run_scenario(sc_name)
        print(json.dumps(res))
    elif cmd == "test":
        res = run_tests()
        print(json.dumps(res))
    elif cmd == "export_zip":
        data = create_zip_archive()
        sys.stdout.buffer.write(data)
    else:
        print(json.dumps({"error": f"Unknown command {cmd}"}))


if __name__ == "__main__":
    main()
