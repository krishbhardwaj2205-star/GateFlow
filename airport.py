"""The baggage logic. Read this file first: it needs only standard Python.

This is a kinematic simulation: distance = belt speed * elapsed time.
The scanner and gate sensors are virtual position checkpoints, not real RFID.
Only one bag enters the conveyor system at a time, which keeps tracking simple.
"""

import csv
from dataclasses import asdict, dataclass
from pathlib import Path


# Change speeds here; changing the layout also requires updating the .wbt world.
NORMAL_SPEED = 1.20                 # metres per simulated second
FRAGILE_SPEED = 0.65                # used in the sorting section
START_X = -5.20
SCANNER_X = -3.90
DELHI_TURN_X = -1.00
MUMBAI_TURN_X = 1.60
STRAIGHT_SECTION_X = 2.50
GATE_DISTANCE = 3.00
BENGALURU_GATE_X = 5.20
GATES = {"Delhi": "A", "Mumbai": "B", "Bengaluru": "C"}
GATE_NAMES = {gate: city for city, gate in GATES.items()}
COLORS = {"A": [0.12, 0.65, 0.95], "B": [0.92, 0.47, 0.12],
          "C": [0.25, 0.78, 0.45]}


@dataclass
class Bag:
    bag_id: str
    destination: str
    category: str
    state: str = "Waiting"
    x: float = START_X
    y: float = 0.0
    entered_at: float | None = None
    finished_at: float | None = None
    expected_gate: str | None = None
    actuator_route: str | None = None
    actual_gate: str | None = None
    fault_applied: bool = False
    processing_time: float | None = None


def load_manifest(path):
    """Read an ordinary CSV, rejecting mistakes before the demonstration starts."""
    bags = []
    seen = set()
    with Path(path).open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"bag_id", "destination", "category"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("CSV needs bag_id,destination,category columns")
        for row in reader:
            bag_id = row["bag_id"].strip()
            city = row["destination"].strip()
            category = row["category"].strip()
            if not bag_id or bag_id in seen:
                raise ValueError(f"Bag IDs must be nonempty and unique: {bag_id!r}")
            if city not in GATES or category not in ("Standard", "Fragile"):
                raise ValueError(f"Invalid destination or category for {bag_id}")
            bags.append(Bag(bag_id, city, category))
            seen.add(bag_id)
    if not bags:
        raise ValueError("The manifest must contain at least one bag")
    return bags


def gate_sensor_at(x, y):
    """Determine which sensor a bag actually reaches, from its coordinates.

    This deliberately does NOT read the expected destination or route command.
    """
    if abs(x - DELHI_TURN_X) < 0.10 and y <= -GATE_DISTANCE:
        return "A"
    if abs(x - MUMBAI_TURN_X) < 0.10 and y >= GATE_DISTANCE:
        return "B"
    if x >= BENGALURU_GATE_X and abs(y) < 0.10:
        return "C"
    return None


class Airport:
    """One small controller; all decisions are in the named methods below."""

    def __init__(self, bags):
        self.bags = bags
        self.time = 0.0
        self.current = None
        self.next_index = 0
        self.paused = False
        self.fault_armed = False
        self.alarm = ""
        self.events = []
        self.gate_counts = {"A": 0, "B": 0, "C": 0}

    def log(self, message):
        self.events.append({"time_s": round(self.time, 2), "message": message})

    def step(self, dt):
        """Called repeatedly by Webots. There are four easy-to-follow stages."""
        if dt <= 0:
            raise ValueError("Time step must be positive")
        if self.complete:
            return  # Keep final KPIs fixed after the batch finishes.
        if self.paused or self.alarm:
            self.time += dt
            return  # Time continues, but the conveyors are stopped.
        if self.current is None:
            self.admit_next_bag()
        self.time += dt
        if self.current is None:
            return
        self.move_bag(dt)
        self.identify_bag()
        self.sort_bag()
        self.verify_arrival()

    def admit_next_bag(self):
        if self.next_index < len(self.bags):
            self.current = self.bags[self.next_index]
            self.next_index += 1
            self.current.entered_at = self.time
            self.current.state = "Check-in conveyor"
            self.log(f"{self.current.bag_id}: admitted at check-in")

    def identify_bag(self):
        bag = self.current
        if bag.state != "At scanner":
            return
        # Simulated tag lookup: the bag record is our virtual RFID tag.
        bag.expected_gate = GATES[bag.destination]
        bag.actuator_route = bag.expected_gate
        if self.fault_armed:
            # Model an actuator sending the bag to a different branch.
            # The tag and expected_gate remain unchanged.
            bag.actuator_route = {"A": "B", "B": "C", "C": "A"}[bag.expected_gate]
            bag.fault_applied = True
            self.fault_armed = False
            self.log(f"{bag.bag_id}: diverter fault injected")
        bag.state = "Sorting conveyor"
        self.log(f"{bag.bag_id}: tag read, {bag.destination}, {bag.category}")

    def belt_speed(self):
        if not self.current or self.paused or self.alarm:
            return 0.0
        if (self.current.category == "Fragile" and
                self.current.state == "Sorting conveyor"):
            return FRAGILE_SPEED
        return NORMAL_SPEED

    def move_bag(self, dt):
        bag = self.current
        distance = self.belt_speed() * dt
        if bag.state == "Check-in conveyor":
            bag.x = min(SCANNER_X, bag.x + distance)
            if bag.x >= SCANNER_X:
                bag.state = "At scanner"
        elif bag.state == "Sorting conveyor":
            # Stop exactly at a transfer point so large steps cannot skip it.
            turn_x = {"A": DELHI_TURN_X, "B": MUMBAI_TURN_X,
                      "C": STRAIGHT_SECTION_X}[bag.actuator_route]
            bag.x = min(turn_x, bag.x + distance)
        elif bag.state == "Destination conveyor":
            if bag.actuator_route == "A":
                bag.y = max(-GATE_DISTANCE, bag.y - distance)
            elif bag.actuator_route == "B":
                bag.y = min(GATE_DISTANCE, bag.y + distance)
            else:
                bag.x = min(BENGALURU_GATE_X, bag.x + distance)

    def sort_bag(self):
        bag = self.current
        if bag.state != "Sorting conveyor":
            return
        turn_x = {"A": DELHI_TURN_X, "B": MUMBAI_TURN_X,
                  "C": STRAIGHT_SECTION_X}[bag.actuator_route]
        if bag.x >= turn_x:
            bag.state = "Destination conveyor"
            self.log(f"{bag.bag_id}: transferred to conveyor {bag.actuator_route}")

    def verify_arrival(self):
        bag = self.current
        if bag.state != "Destination conveyor":
            return
        sensed_gate = gate_sensor_at(bag.x, bag.y)
        if sensed_gate is None:
            return
        bag.actual_gate = sensed_gate
        if sensed_gate == bag.expected_gate:
            bag.state = "Delivered"
            bag.finished_at = self.time
            bag.processing_time = round(self.time - bag.entered_at, 3)
            self.gate_counts[sensed_gate] += 1
            self.log(f"{bag.bag_id}: verified and delivered to gate {sensed_gate}")
            self.current = None
        else:
            bag.state = "Held for inspection"
            self.alarm = (f"MISROUTE: {bag.bag_id} expected gate {bag.expected_gate}, "
                          f"reached gate {sensed_gate}. Conveyor stopped.")
            self.log(self.alarm)

    def apply_command(self, action):
        """Dashboard buttons call these same plain operations."""
        if action == "pause":
            self.paused = True
            self.log("Operator paused the conveyors")
        elif action == "resume":
            self.paused = False
            self.log("Operator resumed the conveyors")
        elif action == "inject_fault":
            self.fault_armed = True
            self.log("Fault armed for the next bag reaching identification")
        elif action == "clear_fault" and self.alarm:
            # Simulate an operator removing the held bag for manual inspection.
            # It is not counted as delivered and is not counted twice as a fault.
            self.current.state = "Removed for inspection"
            self.current.finished_at = self.time
            self.log(f"{self.current.bag_id}: operator removed bag for inspection")
            self.current = None
            self.alarm = ""

    @property
    def complete(self):
        return self.next_index == len(self.bags) and self.current is None

    def snapshot(self):
        delivered = [b for b in self.bags if b.state == "Delivered"]
        verified = [b for b in self.bags if b.actual_gate is not None]
        correct = sum(b.actual_gate == b.expected_gate for b in verified)
        misroutes = sum(b.actual_gate != b.expected_gate for b in verified)
        mean_time = (sum(b.processing_time for b in delivered) / len(delivered)
                     if delivered else None)
        return {
            "time_s": round(self.time, 3), "complete": self.complete,
            "paused": self.paused, "alarm": self.alarm,
            "fault_armed": self.fault_armed, "belt_speed_m_s": self.belt_speed(),
            "current_bag": self.current.bag_id if self.current else None,
            "gate_counts": self.gate_counts.copy(),
            "metrics": {
                "total_bags": len(self.bags), "admitted": self.next_index,
                "delivered": len(delivered), "verified": len(verified),
                "misroutes": misroutes,
                "sorting_accuracy_pct": 100 * correct / len(verified) if verified else None,
                "mean_processing_s": mean_time,
                "throughput_bags_min": 60 * len(delivered) / self.time if self.time else 0,
            },
            "bags": [asdict(bag) for bag in self.bags],
            "events": self.events[-100:],
        }
