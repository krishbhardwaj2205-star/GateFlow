"""Run the same controller without Webots to check logic and the dashboard.

This is explicitly a controller preview, not a Webots simulation.
Example: python preview_controller.py --speed 4
"""

import argparse
import time

from airport import Airport, load_manifest
from shared_files import FileLink, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--speed", type=float, default=1.0, help="Preview speed multiplier")
    parser.add_argument("--fault-at", help="Inject a misroute for this bag ID, e.g. B004")
    parser.add_argument("--auto-clear", action="store_true", help="Remove held bag automatically")
    parser.add_argument("--exit-when-finished", action="store_true")
    args = parser.parse_args()
    if args.speed <= 0:
        parser.error("--speed must be positive")
    airport = Airport(load_manifest(ROOT / "data" / "bags.csv"))
    link = FileLink("Controller preview (no Webots)")
    link.publish(airport, force=True)
    dt = 0.05
    print("Controller preview running. Start dashboard.py in another terminal. Ctrl+C stops.")
    while True:
        action = link.read_command()
        if action == "reset":
            airport = Airport(load_manifest(ROOT / "data" / "bags.csv"))
            link = FileLink("Controller preview (no Webots)")
        elif action:
            airport.apply_command(action)
        if (airport.current and airport.current.bag_id == args.fault_at and
                airport.current.state == "Check-in conveyor"):
            airport.fault_armed = True
        airport.step(dt)
        if args.auto_clear and airport.alarm:
            airport.apply_command("clear_fault")
        link.publish(airport)
        if args.exit_when_finished and airport.complete:
            link.publish(airport, force=True)
            print(airport.snapshot()["metrics"])
            break
        time.sleep(dt / args.speed)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPreview stopped.")
