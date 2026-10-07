"""Meaningful checks of routing, fault handling, timing, and local commands.

Run from the project folder: python -m unittest discover -s tests -v
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from airport import Airport, Bag, GATES, gate_sensor_at, load_manifest
from shared_files import FileLink, read_json, send_command, write_json


def finish_batch(airport, fault_id=None):
    for _ in range(20000):
        if (airport.current and airport.current.bag_id == fault_id and
                airport.current.state == "Check-in conveyor"):
            airport.fault_armed = True
        airport.step(0.032)
        if airport.alarm:
            airport.apply_command("clear_fault")
        if airport.complete:
            return airport.snapshot()
    raise AssertionError("Batch did not complete within the simulated time limit")


class AirportTests(unittest.TestCase):
    def test_all_six_combinations_reach_correct_gates(self):
        bags = [Bag(f"B{i}", city, category)
                for i, (city, category) in enumerate(
                    (city, cat) for city in GATES for cat in ("Standard", "Fragile"))]
        result = finish_batch(Airport(bags))
        self.assertEqual(result["gate_counts"], {"A": 2, "B": 2, "C": 2})
        self.assertEqual(result["metrics"]["sorting_accuracy_pct"], 100)
        self.assertTrue(all(b["actual_gate"] == GATES[b["destination"]] for b in result["bags"]))

    def test_fragile_bag_takes_longer_for_same_destination(self):
        standard = finish_batch(Airport([Bag("S", "Delhi", "Standard")]))
        fragile = finish_batch(Airport([Bag("F", "Delhi", "Fragile")]))
        self.assertGreater(fragile["bags"][0]["processing_time"], standard["bags"][0]["processing_time"])

    def test_misroute_stops_motion_before_delivery(self):
        airport = Airport([Bag("BAD", "Delhi", "Standard"), Bag("OK", "Mumbai", "Fragile")])
        airport.apply_command("inject_fault")
        for _ in range(2000):
            airport.step(0.032)
            if airport.alarm:
                break
        self.assertTrue(airport.alarm)
        bag = airport.current
        self.assertEqual(bag.expected_gate, "A")
        self.assertEqual(bag.actual_gate, "B")
        held_position = (bag.x, bag.y)
        for _ in range(10):
            airport.step(0.032)
        self.assertEqual((bag.x, bag.y), held_position)
        self.assertEqual(sum(airport.gate_counts.values()), 0)
        airport.apply_command("clear_fault")
        result = finish_batch(airport)
        self.assertEqual(result["metrics"]["sorting_accuracy_pct"], 50)
        self.assertEqual(result["metrics"]["misroutes"], 1)
        self.assertEqual(result["metrics"]["delivered"], 1)
        self.assertEqual(result["bags"][0]["state"], "Removed for inspection")

    def test_sensors_use_coordinates_not_destination(self):
        self.assertEqual(gate_sensor_at(-1, -3), "A")
        self.assertEqual(gate_sensor_at(1.6, 3), "B")
        self.assertEqual(gate_sensor_at(5.2, 0), "C")
        self.assertIsNone(gate_sensor_at(-1, 0))

    def test_pause_freezes_motion_but_counts_elapsed_time(self):
        airport = Airport([Bag("B", "Delhi", "Standard")])
        airport.step(0.032)
        before = airport.current.x
        airport.apply_command("pause")
        airport.step(2)
        self.assertEqual(airport.current.x, before)
        self.assertAlmostEqual(airport.time, 2.032)
        airport.apply_command("resume")
        airport.step(0.032)
        self.assertGreater(airport.current.x, before)

    def test_finished_kpis_do_not_decay(self):
        airport = Airport([Bag("B", "Bengaluru", "Standard")])
        result = finish_batch(airport)
        airport.step(100)
        self.assertEqual(airport.snapshot()["metrics"], result["metrics"])

    def test_manifest_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bags.csv"
            path.write_text("bag_id,destination,category\nB1,Delhi,Standard\nB1,Mumbai,Fragile\n")
            with self.assertRaises(ValueError):
                load_manifest(path)

    def test_mailbox_deduplicates_and_ignores_old_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            command = Path(directory) / "command.json"
            status = Path(directory) / "status.json"
            with patch("shared_files.COMMAND_FILE", command), patch("shared_files.STATUS_FILE", status):
                link = FileLink("Test")
                send_command("pause", link.run_id)
                self.assertEqual(link.read_command(), "pause")
                self.assertIsNone(link.read_command())
                new_link = FileLink("Test")
                self.assertIsNone(new_link.read_command())
                new_link.publish(Airport([Bag("B", "Delhi", "Standard")]), force=True)
                self.assertEqual(read_json(status)["source"], "Test")

    def test_windows_reader_lock_is_retried(self):
        import os
        original_replace = os.replace
        calls = []
        def sometimes_locked(source, target):
            calls.append(1)
            if len(calls) < 3:
                raise PermissionError("Simulated Windows reader lock")
            original_replace(source, target)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "status.json"
            with patch("shared_files.os.replace", side_effect=sometimes_locked):
                write_json(path, {"delivered": 2})
            self.assertEqual(read_json(path), {"delivered": 2})
            self.assertEqual(len(list(Path(directory).glob("*.tmp"))), 0)


if __name__ == "__main__":
    unittest.main()
