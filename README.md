# GateFlow — Group 24

A small Smart Airport Baggage Handling project for Robotics & Automation CA3.

**Stack:** Webots R2025a, Python 3.12, Streamlit 1.41.1. The Webots controller itself uses only standard Python plus Webots' built-in controller API.

## What is implemented

- Delhi → Gate A; Mumbai → Gate B; Bengaluru → Gate C.
- Standard and fragile bags. A yellow stripe marks fragile bags; destination colour identifies their intended gate.
- Simulated tag identification at the check-in scanner.
- Conveyor transportation and automatic destination routing.
- Fragile bags use a lower sorting-section speed.
- A deliberately incorrect diverter route is detected at the destination checkpoint.
- The system stops and holds the misrouted bag before gate delivery. An operator can remove it for manual inspection.
- A live dashboard with bag tracking, gate counts, alarms, pause/resume, reset, fault injection, and CSV export.
- Measured first-pass accuracy, mean processing time, and throughput.

## Simulation scope — explain this in the report

This is a **kinematic conveyor simulation**: bag movement follows `distance = belt speed × time`. Webots renders those positions; belt friction, collisions, pneumatic forces, and motor electrical behaviour are not modelled. Identification uses a Python bag record as a virtual tag. Sensors are virtual checkpoints based on bag coordinates. No real barcode/RFID decoding is claimed.

One bag is admitted at a time. This makes tracking and diverter sequencing easy to reproduce. After verification, delivered bags are visually placed on the collection trays. Removing a held bag represents manual intervention; it is not an automatic recovery conveyor.

## First run on Windows

**This computer is prepared:** Webots R2025a is installed at `C:\Users\krish\AppData\Local\Programs\Webots`. This project's `.venv` has Python 3.12.14 and the dashboard dependencies installed. Double-click **`webots.cmd`** to open the airport world paused, then **`dashboard.cmd`**. Press Webots' Run button. The launcher configures the controller interpreter automatically.

**On another computer:** install Python 3.12 and Webots, then double-click `setup.cmd` once. Run `webots.cmd` and `dashboard.cmd`. `preview.cmd` lets you try the controller/dashboard before Webots is installed. The ZIP excludes this computer's virtual environment and absolute interpreter settings; setup recreates them.

1. Install **Python 3.12** from [python.org](https://www.python.org/downloads/). Select the option to add Python to PATH.
2. Install **Webots R2025a** from the [official Cyberbotics release](https://github.com/cyberbotics/webots/releases/tag/R2025a).
3. Open a terminal in this `smart_airport` folder. Run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

Open [the dashboard](http://127.0.0.1:8501) in your browser. It will wait for the controller.

4. In Webots, open **`worlds/airport.wbt`**. The adjacent `controllers/` folder is found automatically.
5. Run `.\.venv\Scripts\python.exe configure_python.py` to create the controller's `runtime.ini` with the correct absolute interpreter path. `setup.cmd` and `webots.cmd` do this automatically. Repeat after moving the project folder.
6. Press Webots' **Run in real time** button. Keep both Webots and the Streamlit terminal open.
7. The dashboard source must say **Webots**. Bags should move, gate counts should rise, and the six destination/category combinations should complete twice.

Optional interpreter override (use your own absolute path, without quotes):

```ini
[python]
COMMAND = C:\your\project\smart_airport\.venv\Scripts\python.exe
```

The project ships with its world and textures already generated. There are no external PROTO/model downloads. Do not run `pip install controller`: that is not the Webots controller module.

## Check the Python and dashboard before installing Webots

Run this in a second terminal while the dashboard is open:

```powershell
.\.venv\Scripts\python.exe preview_controller.py
```

This uses the same baggage logic and JSON connection. The dashboard clearly labels it **Controller preview (no Webots)**. It helps you learn/debug the Python; it is not a replacement for the required Webots demonstration. Stop the preview with Ctrl+C **before** starting Webots, so only one controller writes the status file.

Optional faster preview: `preview_controller.py --speed 4`.

## Demonstration sequence

1. Reset the batch and let the first standard Delhi bag reach Gate A.
2. Show the fragile Mumbai bag moving at **0.65 m/s** in the sorting section, compared with **1.20 m/s** for standard bags.
3. Show a Bengaluru bag taking the straight route to Gate C.
4. Click **Fault on next scan**. The next bag reaching the scanner receives an incorrect actuator route; its tag stays unchanged.
5. At the wrong checkpoint, show the red alarm, stopped belt, expected versus actual gate, and reduced first-pass accuracy.
6. Click **Remove held bag** to simulate manual removal to inspection. Processing resumes.
7. At batch completion, export the bag results CSV and show the final KPI values.

Webots keyboard shortcuts (click inside the 3D view first): **P** pause/resume, **F** fault on next scan, **C** remove held bag, **R** reset.

The dashboard's Pause stops conveyor movement inside the model, while Webots keeps stepping to receive Resume. Pausing Webots itself also pauses command processing; use Webots' Run button to restart it.

## Where to read and edit

| File | Purpose |
|---|---|
| `airport.py` | All routing, speed, sensor, fault, and KPI logic. Start here. |
| `data/bags.csv` | The input baggage manifest. Edit destination/category values here. |
| `controllers/baggage_controller/baggage_controller.py` | Webots stepping, keyboard input, and scene drawing. |
| `webots.cmd` / `configure_python.py` | Open the world and configure its project Python interpreter. |
| `dashboard.py` | Streamlit display and operator buttons. |
| `shared_files.py` | The small local JSON link, including Windows file-lock retries. |
| `preview_controller.py` | An explicitly labelled controller preview without Webots. |
| `build_world.py` | Recreates the supplied world and text textures. |
| `tests/test_airport.py` | Routing, fault, timing, and file-link checks. |
| `EXPLAIN_THE_LOGIC.md` | A step-by-step explanation for reproducing the project and Q&A. |
| `VERIFICATION.md` | What has been tested and what still requires Webots. |

## KPI definitions

**First-pass accuracy** = correct checkpoint arrivals / all verified checkpoint arrivals × 100. A detected misroute counts as an incorrect first pass, even though the system prevents gate delivery. Before any checkpoint arrival, accuracy is undefined (shown as `—`).

**Mean processing time** = average time from check-in admission to correct gate arrival, for delivered bags only. Held and manually removed bags are excluded. Processing time includes pauses that affect that bag.

**Throughput** = delivered bags / elapsed simulation time in minutes. Simulation time includes operator pauses and fault holds; it freezes at batch completion. It is not based on laptop wall-clock speed, so Webots fast mode does not inflate the reported throughput.

## Reproduce the checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe build_world.py
.\.venv\Scripts\python.exe validate_logic.py
```

The world-generation script uses Pillow, installed as a Streamlit dependency. The controller does not need it.
`validate_logic.py` recreates the explicitly labelled controller-only results in `examples/`; use your live demonstration exports for the submission.

## Troubleshooting

- **Dashboard says waiting:** ensure the Webots controller starts and check Webots' console for errors. You can test the connection using the preview command.
- **`No module named controller`:** run the Webots adapter from Webots, not directly in a terminal. Use `preview_controller.py` for terminal testing.
- **`No module named streamlit`:** use this project's `.venv\Scripts\python.exe` for the dashboard command.
- **Old/stale dashboard data:** the controller is stopped or Webots is paused. The app keeps the last snapshot visible and disables controls when data is over five seconds old.
- **Bag held and Resume does nothing:** a latched misroute requires **Remove held bag**. Resume only clears an operator pause.
- **Two controllers interfere:** stop the preview before running Webots. Each batch has a run ID so old commands do not affect a reset batch.
- **Port 8501 already occupied:** stop the other dashboard, or add `--server.port 8502` and open that port.

## Official references

- [Webots controller programming](https://cyberbotics.com/doc/guide/controller-programming?version=R2023b)
- [Webots Supervisor programming](https://cyberbotics.com/doc/guide/supervisor-programming?tab-language=python&version=R2022a)
- [Streamlit periodic fragments](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment)
