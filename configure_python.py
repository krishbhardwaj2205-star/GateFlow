"""Tell Webots to use the same Python environment as the dashboard."""

from pathlib import Path
import sys

root = Path(__file__).resolve().parent
settings = root / "controllers" / "baggage_controller" / "runtime.ini"
settings.write_text(f"[python]\nCOMMAND = {sys.executable}\n", encoding="utf-8")
print("Webots Python:", sys.executable)
