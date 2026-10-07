"""Run with: python -m streamlit run dashboard.py"""

import csv
import html
import io
import time

import streamlit as st
import streamlit.components.v1 as components

from shared_files import STATUS_FILE, read_json, send_command

st.set_page_config(page_title="GateFlow | Baggage Monitor", page_icon="✈", layout="wide")
st.markdown("""<style>
.stApp {background: #0b1422; color: #eaf1fb;}
div[data-testid="stMetric"] {background: #152339; padding: 18px; border-radius: 12px;}
div[data-testid="stMetricLabel"] {color: #b4c5db;}
div[data-testid="stMetricValue"] {color: #eaf1fb;}
div[data-testid="stMetricValue"] {font-size: clamp(1.2rem, 3vw, 2rem);}
.block-container {padding-top: 2rem;}
</style>""", unsafe_allow_html=True)
st.title("✈ GateFlow")
st.caption("GROUP 24 · SMART AIRPORT BAGGAGE HANDLING · Live conveyor monitoring")


def conveyor_map(bags):
    """A small SVG map mirrors controller coordinates; Webots is the 3D view."""
    def point(x, y):
        return 415 + x * 52, 210 - y * 37
    parts = ['<svg viewBox="0 0 850 420" style="width:100%;height:320px" xmlns="http://www.w3.org/2000/svg">',
             '<rect width="850" height="420" rx="16" fill="#152339"/>']
    for x1, y1, x2, y2 in [(-5.65, 0, 5.55, 0), (-1, 0, -1, -3.5), (1.6, 0, 1.6, 3.5)]:
        a, b = point(x1, y1)
        c, d = point(x2, y2)
        parts.append(f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}" stroke="#425775" stroke-width="25"/>')
    labels = [("CHECK-IN", -5.2, -0.9), ("SCANNER", -3.9, 0.9),
              ("A · DELHI", -1, -4.15), ("B · MUMBAI", 1.6, 4.15),
              ("C · BENGALURU", 5.4, 0.9)]
    for label, x, y in labels:
        px, py = point(x, y)
        parts.append(f'<text x="{px}" y="{py}" text-anchor="middle" fill="#c3d2e6" font-size="18" font-family="sans-serif">{label}</text>')
    for bag in bags:
        if bag["state"] in ("Waiting", "Delivered", "Removed for inspection"):
            continue
        x, y = point(bag["x"], bag["y"])
        color = {"Delhi": "#1fa6f2", "Mumbai": "#eb781f", "Bengaluru": "#40c773"}[bag["destination"]]
        if bag["state"] == "Held for inspection":
            color = "#ff4052"
        parts.append(f'<rect x="{x-13}" y="{y-9}" width="26" height="18" rx="3" fill="{color}"/>')
        if bag["category"] == "Fragile":
            parts.append(f'<line x1="{x}" y1="{y-8}" x2="{x}" y2="{y+8}" stroke="#ffe04b" stroke-width="4"/>')
        parts.append(f'<text x="{x}" y="{y-18}" text-anchor="middle" fill="white" font-size="18" font-family="sans-serif">{html.escape(bag["bag_id"])}</text>')
    parts.append('</svg>')
    return "".join(parts)


def bags_csv(bags):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(bags[0]))
    writer.writeheader()
    writer.writerows(bags)
    return output.getvalue()


@st.fragment(run_every=0.5)
def live_dashboard():
    status = read_json(STATUS_FILE)
    if not status:
        st.info("Waiting for the controller. Open worlds/airport.wbt in Webots and press Run.")
        st.code("python preview_controller.py  # Optional controller preview without Webots")
        return
    age = max(0, time.time() - status["updated_at"])
    connected = age < 5
    if connected:
        st.caption(f'Source: {status["source"]} · refreshed {age:.1f}s ago · simulation {status["time_s"]:.1f}s')
    else:
        st.warning(f"Controller is not updating ({age:.0f}s old). Showing the last received data; controls are disabled.")
    if status["source"] != "Webots":
        st.info("Controller preview only — Webots is not running this simulation.")
    if status["alarm"]:
        st.error(status["alarm"])
    elif status["complete"]:
        st.success("Batch complete. Export the results, or reset for another demonstration.")
    elif status["paused"]:
        st.warning("Conveyors paused. Elapsed simulation time continues.")
    metrics = status["metrics"]
    columns = st.columns(4)
    accuracy = metrics["sorting_accuracy_pct"]
    processing = metrics["mean_processing_s"]
    columns[0].metric("Accuracy", "—" if accuracy is None else f"{accuracy:.1f}%")
    columns[1].metric("Avg. time", "—" if processing is None else f"{processing:.1f} s")
    columns[2].metric("Bags / min", f'{metrics["throughput_bags_min"]:.2f}')
    columns[3].metric("Delivered", f'{metrics["delivered"]} / {metrics["total_bags"]}')
    st.caption(f'{metrics["verified"]} bags verified · {metrics["misroutes"]} misroutes detected and held')

    if st.session_state.get("run_id") != status["run_id"]:
        st.session_state.run_id = status["run_id"]
        st.session_state.pending = None
    pending = st.session_state.get("pending")
    if pending == status.get("last_command_id"):
        st.session_state.pending = None
        pending = None
    disabled = not connected or pending is not None
    buttons = st.columns(5)
    commands = [("Resume" if status["paused"] else "Pause", "resume" if status["paused"] else "pause"),
                ("Fault on next scan", "inject_fault"), ("Remove held bag", "clear_fault"),
                ("Reset batch", "reset")]
    for column, (label, action) in zip(buttons, commands):
        unavailable = disabled or (status["complete"] and action != "reset")
        unavailable = unavailable or (action == "clear_fault" and not status["alarm"])
        if column.button(label, disabled=unavailable, use_container_width=True):
            st.session_state.pending = send_command(action, status["run_id"])
            st.rerun()
    buttons[4].download_button("Export bags CSV", bags_csv(status["bags"]), "bag_results.csv", "text/csv", use_container_width=True)
    if pending:
        st.caption("Waiting for the controller to acknowledge the command…")
    if status["fault_armed"]:
        st.warning("Misroute fault armed for the next bag reaching the scanner.")
    components.html(conveyor_map(status["bags"]), height=330)
    st.caption(f'Active bag: {status["current_bag"] or "—"} · Sorting belt speed: {status["belt_speed_m_s"]:.2f} m/s')
    for column, (gate, city) in zip(st.columns(3), [("A", "Delhi"), ("B", "Mumbai"), ("C", "Bengaluru")]):
        column.metric(f"{gate} · {city}", status["gate_counts"][gate])
    st.subheader("Baggage tracking")
    fields = ["bag_id", "destination", "category", "state", "expected_gate", "actual_gate", "processing_time"]
    st.dataframe([{key: bag[key] for key in fields} for bag in status["bags"]], use_container_width=True, hide_index=True)
    with st.expander("Event log"):
        st.dataframe(list(reversed(status["events"])), use_container_width=True, hide_index=True)
    with st.expander("How the KPIs are calculated"):
        st.write("Accuracy = bags verified at their correct gate / all verified bags × 100. A held misroute still counts as an incorrect first pass.")
        st.write("Processing time = check-in admission to correct gate arrival, averaged over delivered bags. Held/inspection bags are excluded.")
        st.write("Throughput = delivered bags / elapsed simulated minutes. Operator pauses and fault holds count toward elapsed time. Final metrics freeze when the batch completes.")


live_dashboard()
