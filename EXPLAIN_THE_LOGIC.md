# Read the Python in this order

The important file is `airport.py`. It works without Webots or Streamlit, so you can understand it as an ordinary Python program.

## 1. Each bag is one record

The `Bag` dataclass holds its ID, destination, category, position, and state. The tag values are loaded from `data/bags.csv`. For example, `B001,Delhi,Standard` means bag B001 should eventually arrive at gate A.

`expected_gate` comes from the tag. `actuator_route` describes the branch the diverter actually sends it toward. `actual_gate` is populated only when a position checkpoint detects the bag. Keeping these three values separate lets us demonstrate a genuine routing mismatch.

## 2. The controller runs in small time steps

Webots calls `airport.step(0.032)` every 32 simulated milliseconds. Each step has this sequence:

```python
move_bag(dt)
identify_bag()
sort_bag()
verify_arrival()
```

The controller first admits a bag if the system is empty. It processes one bag at a time, so it does not need a queue-tracking algorithm or complex conveyor synchronization.

## 3. Movement is just speed multiplied by time

For a bag moving at 1.20 m/s for 0.032 seconds:

```python
distance = 1.20 * 0.032  # 0.0384 metres
bag.x = bag.x + distance
```

`min()` and `max()` stop the bag exactly at a scanner, transfer point, or gate checkpoint. This prevents it from jumping past a checkpoint when the time step is larger.

The Webots adapter draws the resulting positions. This is a simplified kinematic conveyor model, not a friction/collision simulation.

## 4. Identification looks up the intended gate

At the scanner, the virtual tag is read:

```python
bag.expected_gate = GATES[bag.destination]
bag.actuator_route = bag.expected_gate
```

The normal route is therefore A for Delhi, B for Mumbai, and C for Bengaluru. The destination colour is a visual aid, while the data record determines the route.

## 5. Sorting changes the direction of movement

- Gate A: advance along the main belt to x = -1, then move toward negative y.
- Gate B: advance to x = 1.6, then move toward positive y.
- Gate C: continue straight toward positive x.

A bag's state changes from `Sorting conveyor` to `Destination conveyor` at its transfer point. The visible diverter arm follows the actuator route.

## 6. Fragile handling changes the sorting speed

`belt_speed()` returns 0.65 m/s when the active bag is fragile and in the sorting section. Otherwise it returns 1.20 m/s. A pause or fault makes the speed zero.

Try changing `FRAGILE_SPEED` from 0.65 to 0.45, resetting the simulation, and comparing the measured processing time. The rest of the routing logic stays the same.

## 7. A fault changes the actuator response

The fault button sets `fault_armed = True`. The next scan consumes that flag and chooses an incorrect actuator route:

```python
bag.actuator_route = {"A": "B", "B": "C", "C": "A"}[bag.expected_gate]
```

The bag ID and expected gate do not change. The bag visibly travels along a wrong destination conveyor.

## 8. Verification uses the arrival position

`gate_sensor_at(x, y)` checks coordinates. It does not use the expected destination or route command.

The controller compares the sensed gate with the expected gate. A match increments the gate counter. A mismatch sets the alarm and holds the bag. The operator's removal command places it in the inspection display and allows the next bag to enter. Removed bags are excluded from delivery totals.

## 9. The dashboard reads a snapshot

Every quarter of a wall-clock second, `shared_files.py` writes `runtime/status.json`. Streamlit refreshes its display every half second. It can also write one operator command to `runtime/command.json`.

Each command has a unique ID and the current run ID. The controller acknowledges it and ignores duplicate/stale commands. The dashboard disables further commands until acknowledgement, preventing its single-command mailbox from being overwritten by rapid clicks in one session. Use one operator dashboard session for the demonstration.

File writes use a temporary file followed by an atomic replacement. Short Windows lock retries prevent a dashboard read from stopping the simulation.

## 10. Reproduce it yourself

1. Read `Bag`, `GATES`, and the speed constants.
2. Follow one standard Delhi bag through the four step functions.
3. Follow a fragile bag and find where its speed changes.
4. Follow a faulted bag and explain expected/actuator/actual gate.
5. Read `snapshot()` to understand every KPI.
6. Read the Webots adapter's `main()` loop.
7. Read `FileLink.publish()` and then the dashboard.

For Q&A, describe the identification and conveyor physics as simulated abstractions. Explain that the project demonstrates destination-based control, category-sensitive handling, verification, and monitoring.
