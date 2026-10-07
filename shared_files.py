"""Small local-file link between the controller and the dashboard."""

import json
import os
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# An override is useful for tests. Normally both programs use runtime/.
RUNTIME = Path(os.environ.get("AIRPORT_RUNTIME", ROOT / "runtime"))
STATUS_FILE = RUNTIME / "status.json"
COMMAND_FILE = RUNTIME / "command.json"


def write_json(path, data):
    """Write a complete temporary file, then replace the old file atomically.

    This keeps readers from seeing half a JSON document. A unique temporary
    name also avoids clashes between two dashboard sessions.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        # Windows may briefly lock the target while Streamlit reads it.
        # A short retry lets the reader close its handle before replacement.
        for attempt in range(6):
            try:
                os.replace(temp, path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.01)
    finally:
        temp.unlink(missing_ok=True)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


class FileLink:
    def __init__(self, source):
        self.source = source
        self.run_id = uuid.uuid4().hex
        self.last_command_id = None
        self.last_write = 0.0

    def read_command(self):
        command = read_json(COMMAND_FILE)
        if not command or command.get("run_id") != self.run_id:
            return None  # Old commands must not affect a newly reset run.
        if command.get("id") == self.last_command_id:
            return None
        self.last_command_id = command.get("id")
        return command.get("action")

    def publish(self, airport, force=False):
        now = time.time()
        if not force and now - self.last_write < 0.25:
            return
        data = airport.snapshot()
        data.update(source=self.source, run_id=self.run_id,
                    updated_at=now, last_command_id=self.last_command_id)
        try:
            write_json(STATUS_FILE, data)
        except PermissionError:
            if force:
                raise
            return  # Retry the snapshot next step; never stop conveyor control.
        self.last_write = now


def send_command(action, run_id):
    command_id = uuid.uuid4().hex
    write_json(COMMAND_FILE, {"id": command_id, "action": action, "run_id": run_id})
    return command_id
