"""Create repeatable controller-only results; this does not launch Webots."""

import csv
import json
from pathlib import Path

from airport import Airport, load_manifest

ROOT = Path(__file__).resolve().parent


def run_batch(fault_id=None):
    airport = Airport(load_manifest(ROOT / "data" / "bags.csv"))
    for _ in range(20000):
        if (airport.current and airport.current.bag_id == fault_id and
                airport.current.state == "Check-in conveyor"):
            airport.fault_armed = True
        airport.step(0.032)
        if airport.alarm:
            airport.apply_command("clear_fault")  # No operator wait in this validation.
        if airport.complete:
            return airport.snapshot()
    raise RuntimeError("Batch did not complete")


def main():
    folder = ROOT / "examples"
    folder.mkdir(exist_ok=True)
    results = {"source": "Python controller validation, not a Webots run",
               "timestep_s": 0.032,
               "fault_note": "B004 receives a misroute; manual removal is simulated immediately."}
    for name, fault_id in [("normal", None), ("one_misroute", "B004")]:
        result = run_batch(fault_id)
        results[name] = {"metrics": result["metrics"], "time_s": result["time_s"],
                         "gate_counts": result["gate_counts"]}
        with (folder / f"{name}_bags.csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(result["bags"][0]))
            writer.writeheader()
            writer.writerows(result["bags"])
    (folder / "controller_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
