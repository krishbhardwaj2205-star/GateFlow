"""Webots adapter. The understandable control logic lives in airport.py."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from controller import Supervisor
from airport import Airport, COLORS, GATES, load_manifest
from shared_files import FileLink


class Scene:
    """Draw model positions and actuator states; do not decide destinations here."""

    def __init__(self, supervisor):
        self.supervisor = supervisor
        self.children = supervisor.getRoot().getField("children")
        self.bag_nodes = {}
        self.phase = 0.0
        self.diverters = {gate: supervisor.getFromDef("DIVERTER_" + gate)
                          .getField("rotation") for gate in ("A", "B")}
        self.beacons = {gate: supervisor.getFromDef("BEACON_" + gate)
                        .getField("baseColor") for gate in ("A", "B", "C")}
        self.slats = [supervisor.getFromDef(f"SLAT_{i}").getField("translation")
                      for i in range(18)]

    def add_bag(self, bag, index):
        color = " ".join(str(c) for c in COLORS[GATES[bag.destination]])
        stripe = "1 0.85 0.12" if bag.category == "Fragile" else "0.93 0.95 1"
        # Basic shapes keep the world self-contained; no model downloads needed.
        self.children.importMFNodeFromString(-1, f'''
DEF BAG_{index} Solid {{
  translation {bag.x} {bag.y} 0.85
  name "{bag.bag_id}"
  children [
    Shape {{ appearance PBRAppearance {{ baseColor {color} roughness 0.65 metalness 0 }}
            geometry Box {{ size 0.52 0.38 0.40 }} }}
    Transform {{ translation 0 0 0.205 children [
      Shape {{ appearance PBRAppearance {{ baseColor {stripe} roughness 1 metalness 0 }}
              geometry Box {{ size 0.10 0.39 0.02 }} }} ] }}
  ]
  boundingObject Box {{ size 0.52 0.38 0.40 }}
}}''')
        self.bag_nodes[bag.bag_id] = self.supervisor.getFromDef(f"BAG_{index}")

    def reset(self):
        for node in self.bag_nodes.values():
            node.remove()
        self.bag_nodes.clear()
        self.phase = 0.0

    def draw(self, airport, dt):
        parked_counts = {"A": 0, "B": 0, "C": 0, "inspection": 0}
        for index, bag in enumerate(airport.bags):
            if bag.state == "Waiting":
                continue
            if bag.bag_id not in self.bag_nodes:
                self.add_bag(bag, index)
            x, y = bag.x, bag.y
            if bag.state == "Delivered":
                slot = parked_counts[bag.actual_gate]
                parked_counts[bag.actual_gate] += 1
                if bag.actual_gate == "A":
                    x, y = -1.70 + slot % 3 * 0.65, -3.70 - slot // 3 * 0.48
                elif bag.actual_gate == "B":
                    x, y = 0.90 + slot % 3 * 0.65, 3.70 + slot // 3 * 0.48
                else:
                    x, y = 5.75 + slot // 3 * 0.60, -0.65 + slot % 3 * 0.65
            elif bag.state == "Removed for inspection":
                slot = parked_counts["inspection"]
                parked_counts["inspection"] += 1
                x, y = -5.50 + slot % 3 * 0.65, 3.65 + slot // 3 * 0.48
            node = self.bag_nodes[bag.bag_id]
            node.getField("translation").setSFVec3f([x, y, 0.85])
            if bag.state in ("Held for inspection", "Removed for inspection"):
                shape = node.getField("children").getMFNode(0)
                shape.getField("appearance").getSFNode().getField("baseColor").setSFColor([1, 0.15, 0.20])
        bag = airport.current
        route = bag.actuator_route if bag else None
        self.diverters["A"].setSFRotation([0, 0, 1, -0.80 if route == "A" else 0])
        self.diverters["B"].setSFRotation([0, 0, 1, 0.80 if route == "B" else 0])
        for gate, beacon in self.beacons.items():
            color = [1, 0.12, 0.15] if airport.alarm and bag.actual_gate == gate else COLORS[gate]
            beacon.setSFColor(color)
        self.phase += airport.belt_speed() * dt
        for index, slat in enumerate(self.slats):
            x = -5.65 + (index * 0.62 + self.phase) % 11.16
            slat.setSFVec3f([x, 0, 0.658])
        status = "FAULT: remove held bag for inspection" if airport.alarm else (
            "BATCH COMPLETE" if airport.complete else "PAUSED" if airport.paused else "RUNNING")
        self.supervisor.setLabel(0, "GATEFLOW | Group 24 | " + status, 0.02, 0.02, 0.055, 0xFFFFFF, 0, "Arial")
        description = f"{bag.bag_id} | {bag.destination} | {bag.category} | {bag.state}" if bag else "Waiting / batch complete"
        self.supervisor.setLabel(1, description, 0.02, 0.09, 0.038, 0xD4E8FF, 0, "Arial")
        self.supervisor.setLabel(2, "P: pause/resume  F: next scan misroute  C: remove held bag  R: reset", 0.02, 0.95, 0.030, 0xD4E8FF, 0, "Arial")


def main():
    supervisor = Supervisor()
    timestep = int(supervisor.getBasicTimeStep())
    keyboard = supervisor.getKeyboard()
    keyboard.enable(timestep)
    scene = Scene(supervisor)
    airport = Airport(load_manifest(ROOT / "data" / "bags.csv"))
    link = FileLink("Webots")
    link.publish(airport, force=True)
    previous_key = -1
    while supervisor.step(timestep) != -1:
        action = link.read_command()
        key = keyboard.getKey()
        if key != -1 and key != previous_key:
            shortcuts = {ord("F"): "inject_fault", ord("C"): "clear_fault", ord("R"): "reset"}
            action = shortcuts.get(key, action)
            if key == ord("P"):
                action = "resume" if airport.paused else "pause"
        previous_key = key
        if action == "reset":
            scene.reset()
            airport = Airport(load_manifest(ROOT / "data" / "bags.csv"))
            link = FileLink("Webots")
        elif action:
            airport.apply_command(action)
        airport.step(timestep / 1000)
        scene.draw(airport, timestep / 1000)
        link.publish(airport)


if __name__ == "__main__":
    main()
