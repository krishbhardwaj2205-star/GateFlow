# Verification of the first version

Checked on 5–6 October 2026 using Windows, Webots R2025a, Python 3.12.14, and Streamlit 1.41.1.

## Completed checks

- **9 automated tests passed.** They cover all six destination/category combinations, fragile timing, misroute detection and hold, actual-position checkpoint selection, pause timing, stable final KPIs, duplicate manifest IDs, command deduplication/run IDs, and Windows reader-lock retries.
- Python source files compiled successfully.
- A live Python controller preview was connected to the actual Streamlit app in a browser. Bag status and gate counters updated. Fault injection produced a wrong route and red alarm; manual removal resumed the batch. Reset started a new batch, and Pause changed the belt speed to zero and the button to Resume.
- Stale data was correctly identified and controls disabled after a stopped controller.
- The dashboard layout was visually checked at the narrow in-app browser width, and metric labels/map layout adjusted for readability.
- The generated world was checked against the official Webots R2025a native node schemas: 15 native node types, 53 unique DEF names, and 6 existing local textures. This is a static syntax/schema check.
- Webots was installed successfully for the current Windows account, and its version command confirmed R2025a. The project interpreter is configured using `runtime.ini`; the actual Webots console confirmed that it launched the project `.venv` Python.
- The actual 3D world was run. An initial camera orientation error and invalid Billboard placement were fixed. The corrected world renders the conveyors, all three destination signs, scanner, moving bags, diverters, and inspection tray without those scene warnings.
- An actual Webots batch delivered **12/12 bags**, four to each gate, at **100% accuracy**. Its processing time and throughput matched the controller-only normal result below. The snapshot is `examples/webots_normal_run.json`.
- In a second actual Webots run, B007 retained its Gate A identification but followed the injected Gate B route. It was held at B, the alarm appeared in the live dashboard, and belt speed became zero. Clicking **Remove held bag** in Streamlit cleared the alarm, moved the red bag to the inspection tray, and resumed processing. Screenshots are in `examples/`.
- That Webots fault batch finished with **11/12 delivered**, **91.67% first-pass accuracy**, **9.702 s mean delivered-bag processing time**, and **4.272 bags/min throughput** over **154.496 s**. This includes the actual operator hold while inspecting the alarm. Its snapshot is `examples/webots_fault_run.json`; it differs from the immediate-recovery controller-only example below.
- Webots reported an unsupported Intel GPU and automatically disabled shadows and anti-aliasing. The simple scene rendered and ran near real time during inspection; performance may vary on other computers.

## Repeatable controller results

These results come from `python validate_logic.py` at a 32 ms step, **not from a Webots run**. In the fault run, B004 is misrouted and removed for inspection immediately, with no operator waiting time.

| Measure | Normal batch | One misroute |
|---|---:|---:|
| Delivered | 12/12 | 11/12 |
| Misroutes detected | 0 | 1 |
| First-pass accuracy | 100% | 91.67% |
| Mean delivered-bag processing time | 9.397 s | 9.516 s |
| Throughput | 6.385 bags/min | 5.652 bags/min |
| Batch simulation time | 112.768 s | 116.768 s |

The detailed controller results and per-bag CSVs are in `examples/`. Run your actual demonstration and export its results for the submission; operator pauses will change processing times and throughput.

## Scope of verification

The Webots world, rendering adapter, normal sorting, injected misroute, and dashboard recovery have been exercised. Keyboard shortcuts have not been separately checked. A submission video, PPT, and report have not yet been produced.

This project currently demonstrates kinematic conveyor movement and virtual tag/checkpoint sensors. It does not simulate belt-contact physics or actual RFID decoding.
