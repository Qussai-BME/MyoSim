"""MyoSim — interactive research demonstrator (Streamlit front end).

This app is a thin, read-only presentation layer over the ``myosim`` package.
It does not add, change, or reimplement any control, physics, safety, or task
logic: every simulation call below goes through the exact same public runners
and backends the ``myosim`` CLI uses (see ``src/myosim/cli/main.py``). This
file only arranges their output for a browser.

Because Streamlit Community Cloud containers are shared and ephemeral, this
app deliberately avoids writing permanent run evidence under ``artifacts/``
on every click (unlike the CLI's ``registry.py``, which is the right choice
for a local research workstation). Results are held in ``st.session_state``
and any files that library calls need are written to a ``TemporaryDirectory``
that is cleaned up immediately after use.

Run locally with:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any

import streamlit as st

from myosim import __version__
from myosim.core.config import load_config
from myosim.core.errors import MyoSimError
from myosim.core.types import as_discrete_event
from myosim.experiments.basic_task_runner import run_grasp_evaluation, run_reach_evaluation
from myosim.experiments.task_runner import PickPlaceExperimentRunner, TaskRunResult
from myosim.hardware_twin import FaultKind, FaultWindow, load_hand_profiles
from myosim.metrics.reporting import write_task_markdown_report
from myosim.rendering.overlays import DebugOverlay
from myosim.rendering.recorder import FrameRecorder
from myosim.runtime import resource_root
from myosim.signals.replay import CsvIntentReplay
from myosim.simulation.factory import backend_status, create_backend

# A publisher may set this without baking an unverified public URL into a release.
REPOSITORY_URL = os.environ.get(
    "MYOSIM_REPOSITORY_URL", "https://github.com/Qussai-BME/MyoSim"
).strip()

REPO_ROOT = resource_root()
DEMO_CONFIG_PATH = REPO_ROOT / "configs" / "demo.yaml"
REACH_CONFIG_PATH = REPO_ROOT / "configs" / "tasks" / "reach.yaml"
GRASP_CONFIG_PATH = REPO_ROOT / "configs" / "tasks" / "grasp.yaml"
DEFAULT_REPLAY_PATH = REPO_ROOT / "examples" / "intents" / "pick_place_replay.csv"
HAND_MODEL_PATH = REPO_ROOT / "assets" / "models" / "hand.xml"
R23_ROOT = REPO_ROOT / "artifacts" / "r2_3_real_emg"
HARDWARE_TWIN_PROFILE_PATH = REPO_ROOT / "configs" / "hardware_twin" / "default_hand_v1.yaml"

NON_CLINICAL_NOTICE = (
    "**Research scope only.** MyoSim is not a medical device, is not clinically "
    "validated, and must not be represented as safe or ready for patient "
    "deployment. This page runs a deterministic, software-only simulation — a "
    "synthetic or replayed intent stream through confidence-gated control into a "
    "MuJoCo virtual hand. The clean/debug clips and metrics below are "
    "explanatory engineering artifacts, not proof of physical or clinical "
    "performance."
)

SYSTEM_CHAIN = (
    "Intent source -> confidence and temporal logic -> command state machine\n"
    "-> bounded motion targets -> physics backend -> virtual hand/task -> metrics and provenance"
)

REPLAY_CSV_HELP = (
    "Required columns: `timestamp_s`, `label`, `confidence`. Optional: "
    "`source_subject`, `modality`, `model_version`, `window_id`. "
    "`label` must be one of REST, OPEN, CLOSE, PINCH."
)


st.set_page_config(
    page_title="MyoSim — Motor-Intent to Virtual Prosthetic-Control Demonstrator",
    page_icon="🖐️",
    layout="wide",
)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def render_gif(data: bytes, caption: str, width: int = 480) -> None:
    """Embed GIF bytes as a base64 data URI so the browser animates it natively.

    st.image() has a long-standing history of not reliably animating local
    GIF files (only the first frame renders in some Streamlit versions), so
    this app renders GIFs as a plain <img> tag instead, which every browser
    animates correctly regardless of that.
    """
    b64 = base64.b64encode(data).decode("ascii")
    st.markdown(
        f'<img src="data:image/gif;base64,{b64}" '
        f'style="width:100%;max-width:{width}px;border-radius:8px;border:1px solid #ddd;" '
        f'alt="{caption}">',
        unsafe_allow_html=True,
    )
    st.caption(caption)


@st.cache_resource(show_spinner=False)
def get_environment_status() -> dict[str, Any]:
    """Mirror `myosim doctor`: truthful local backend availability and a
    headless load/reset/step smoke check for each available backend."""
    checks: dict[str, Any] = {"package_version": __version__}
    for name, status in backend_status().items():
        checks[f"{name}_availability"] = status
        if status != "available":
            continue
        backend = create_backend(name)
        try:
            backend.load_model(HAND_MODEL_PATH)
            result = backend.step(steps=1)
            checks[f"{name}_headless_load_reset_step"] = not result.invalid_state
            checks[f"{name}_controllable_joint_count"] = len(backend.joint_names)
        except Exception as exc:  # noqa: BLE001 - surfaced verbatim to the UI
            checks[f"{name}_headless_load_reset_step"] = False
            checks[f"{name}_error"] = str(exc)
        finally:
            backend.close()
    return checks


def run_pick_place(
    replay_path: Path,
    *,
    hardware_twin_delay_s: float | None = None,
    hardware_twin_faults: tuple[FaultWindow, ...] = (),
) -> dict[str, Any]:
    """Run the flagship physics-backed pick-and-place task and capture GIFs.

    This calls the exact same `PickPlaceExperimentRunner` the CLI's
    `myosim run-task --task pick_place --record` command uses.
    """
    config = load_config(DEMO_CONFIG_PATH)
    source = CsvIntentReplay(replay_path)
    recorder_box: dict[str, FrameRecorder] = {}

    def on_step(backend: Any, event: Any, control: Any, task_step: Any) -> None:
        if "recorder" not in recorder_box:
            recorder_box["recorder"] = FrameRecorder(
                backend,
                config.simulation.render_width,
                config.simulation.render_height,
                config.recording.fps,
            )
        recorder_box["recorder"].capture(
            DebugOverlay(
                timestamp_s=event.timestamp_s,
                intent=as_discrete_event(event).label.value,
                confidence=event.confidence,
                controller_state=control.state_output.state.value,
                task_state=task_step.state.value,
                joint_targets_rad=control.targets.positions_rad,
            )
        )

    result: TaskRunResult = PickPlaceExperimentRunner(
        config,
        REPO_ROOT,
        hardware_twin_delay_s=hardware_twin_delay_s,
        hardware_twin_faults=hardware_twin_faults,
        hardware_twin_profiles=(
            load_hand_profiles(HARDWARE_TWIN_PROFILE_PATH)
            if hardware_twin_delay_s is not None
            else None
        ),
        hardware_twin_profile_source=(
            "configs/hardware_twin/default_hand_v1.yaml"
            if hardware_twin_delay_s is not None
            else None
        ),
        hardware_twin_profile_sha256=(
            sha256(HARDWARE_TWIN_PROFILE_PATH.read_bytes()).hexdigest()
            if hardware_twin_delay_s is not None
            else None
        ),
    ).run(source, on_step=on_step)

    clean_bytes = debug_bytes = None
    report_text = ""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        if "recorder" in recorder_box:
            clean_path, debug_path = recorder_box["recorder"].write(tmp_path, stem="pick_place")
            clean_bytes = clean_path.read_bytes()
            debug_bytes = debug_path.read_bytes()
        report_path = write_task_markdown_report(result, tmp_path)
        report_text = report_path.read_text(encoding="utf-8")

    return {
        "result": result,
        "clean_gif": clean_bytes,
        "debug_gif": debug_bytes,
        "report_md": report_text,
    }


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------

st.title("🖐️ MyoSim")
st.caption(
    f"Reproducible motor-intent to simulated-action research demonstrator · "
    f"v{__version__} · Apache-2.0"
)
st.warning(NON_CLINICAL_NOTICE, icon="⚠️")

with st.sidebar:
    st.header("MyoSim")
    st.write(
        "A local-first, software-only research demonstrator for reproducible "
        "simulation of the path from motor-intent events to bounded virtual "
        "prosthetic action."
    )
    st.code(SYSTEM_CHAIN, language=None)
    if REPOSITORY_URL:
        st.markdown(f"[Source code and release notes]({REPOSITORY_URL})")
    else:
        st.caption("Canonical source URL is supplied by the release publisher.")
    st.markdown("Licence: Apache-2.0 · Cite via `CITATION.cff`")
    st.divider()
    st.caption(
        "This demo mirrors the `myosim` CLI exactly — it calls the same "
        "public runners and adds no new simulation, control, or safety logic."
    )

(
    tab_pick_place,
    tab_reach_grasp,
    tab_environment,
    tab_console,
    tab_hardware_twin,
    tab_about,
) = st.tabs(
    [
        "🤖 Pick & place",
        "🎯 Reach & grasp",
        "🩺 Environment status",
        "🔬 R2.3 Evidence",
        "⚙️ Hardware Twin",
        "ℹ️ About",
    ]
)


# --------------------------------------------------------------------------
# Tab: Pick & place (flagship physics-backed demo)
# --------------------------------------------------------------------------

with tab_pick_place:
    st.subheader("Physics-backed pick-and-place benchmark")
    st.write(
        "Replays a chronological stream of motor-intent events through the "
        "confidence-gated control pipeline and a MuJoCo virtual hand. A "
        "decoded CLOSE/PINCH command activates a virtual grasp weld once the "
        "hand reaches the object; the arm then transports it to the target "
        "zone, where a decoded RELEASE/REST command lets go."
    )

    uploaded = st.file_uploader(
        "Optional: upload your own intent replay CSV (otherwise the bundled example is used)",
        type="csv",
        help=REPLAY_CSV_HELP,
    )
    st.caption(REPLAY_CSV_HELP)

    run_clicked = st.button("▶ Run pick-and-place demo", type="primary")

    if run_clicked:
        tmp_upload_path: Path | None = None
        try:
            if uploaded is not None:
                tmp_upload_path = Path(tempfile.mkstemp(suffix=".csv")[1])
                tmp_upload_path.write_bytes(uploaded.getvalue())
                replay_path = tmp_upload_path
            else:
                replay_path = DEFAULT_REPLAY_PATH

            with st.spinner("Running the deterministic simulation and rendering frames..."):
                st.session_state["pick_place"] = run_pick_place(replay_path)
        except MyoSimError as exc:
            st.error(f"MyoSim rejected this run: {exc}")
        except Exception as exc:  # noqa: BLE001 - shown verbatim for diagnosis
            st.error(
                "The simulation could not complete. This is usually a headless-"
                f"rendering setup issue on this deployment rather than a code bug: {exc}\n\n"
                "Check the **Environment status** tab. If MuJoCo loads/steps fine there "
                "but rendering fails here specifically, see the troubleshooting note in "
                "README.md (falling back to `MUJOCO_GL=osmesa` with `libosmesa6` in "
                "`packages.txt` usually resolves it)."
            )
        finally:
            if tmp_upload_path is not None:
                tmp_upload_path.unlink(missing_ok=True)

    payload = st.session_state.get("pick_place")
    if payload is None:
        st.info("Click **Run pick-and-place demo** to simulate a run.")
    else:
        result: TaskRunResult = payload["result"]
        task = result.task_metrics
        control = result.control_metrics

        cols = st.columns(4)
        cols[0].metric("Outcome", "✅ Success" if task.success else "❌ Failed", task.final_state)
        cols[1].metric(
            "Completion time",
            f"{task.completion_time_s:.2f} s" if task.completion_time_s is not None else "—",
        )
        cols[2].metric("Path length", f"{task.path_length_m:.3f} m")
        cols[3].metric("Final target error", f"{task.final_error_m:.3f} m")

        if payload["clean_gif"] and payload["debug_gif"]:
            gif_cols = st.columns(2)
            with gif_cols[0]:
                render_gif(payload["clean_gif"], "Clean render")
            with gif_cols[1]:
                render_gif(
                    payload["debug_gif"],
                    "Debug overlay (intent, controller/task state, confidence)",
                )
            dl_cols = st.columns(2)
            dl_cols[0].download_button(
                "Download clean GIF", payload["clean_gif"], file_name="pick_place_clean.gif"
            )
            dl_cols[1].download_button(
                "Download debug GIF", payload["debug_gif"], file_name="pick_place_debug.gif"
            )
        else:
            st.warning(
                "No recording was produced for this run (rendering may be unavailable "
                "in this environment). Metrics below are still valid — they come from "
                "physics, not from rendering."
            )

        with st.expander("Task & control metrics (raw)"):
            m_cols = st.columns(2)
            m_cols[0].json(task.to_dict())
            m_cols[1].json(control.to_dict())

        with st.expander("Run report (`report.md`)"):
            st.markdown(payload["report_md"])

        with st.expander("Provenance"):
            st.json(result.provenance.to_dict())


# --------------------------------------------------------------------------
# Tab: Reach & grasp (lightweight declarative evaluators, no rendering)
# --------------------------------------------------------------------------

with tab_reach_grasp:
    st.subheader("Reach & grasp evaluators")
    st.write(
        "These are declarative, non-physics evaluations of the reach and grasp "
        "task/metrics machinery against their configured success thresholds — "
        "not MuJoCo-rendered runs. The pick-and-place task above is the only V1 "
        "benchmark that drives full physics end to end; see `docs/limitations.md`."
    )
    try:
        reach = run_reach_evaluation(load_config(REACH_CONFIG_PATH), REPO_ROOT)
        grasp = run_grasp_evaluation(load_config(GRASP_CONFIG_PATH), REPO_ROOT)

        col_reach, col_grasp = st.columns(2)
        with col_reach:
            st.markdown("**Reach**")
            st.metric("Outcome", "✅ Success" if reach.success else "❌ Failed")
            st.json(reach.metrics)
        with col_grasp:
            st.markdown("**Grasp**")
            st.metric("Outcome", "✅ Stable" if grasp.success else "❌ Unstable")
            st.json(grasp.metrics)
    except MyoSimError as exc:
        st.error(f"MyoSim rejected this evaluation: {exc}")


# --------------------------------------------------------------------------
# Tab: Environment status (mirrors `myosim doctor`)
# --------------------------------------------------------------------------

with tab_environment:
    st.subheader("Backend availability (`myosim doctor` equivalent)")
    st.write(
        "Truthful local availability for each declared physics backend, plus a "
        "headless load/reset/step smoke check — exactly what `myosim doctor "
        "--strict` reports on the command line."
    )
    if st.button("Re-check now"):
        get_environment_status.clear()
    st.json(get_environment_status())
    st.caption(
        "This deployment intentionally installs only the MuJoCo backend (the V1 "
        "primary backend) to keep the Streamlit Cloud build fast — PyBullet is an "
        "optional compatibility backend and will show as unavailable here unless "
        "you add the `pybullet` extra yourself."
    )


# --------------------------------------------------------------------------
# Tab: R2.3 real-data downstream evidence (read-only)
# --------------------------------------------------------------------------

with tab_console:
    st.subheader("R2.3 · Recorded sEMG-derived intent to simulated action")
    st.write(
        "This console reads the frozen R2.3 evidence bundle. The upstream predictions "
        "are derived from recorded NinaPro DB3/DB7 data; the downstream task remains "
        "an offline software simulation, not a physical prosthesis test."
    )
    manifest_path = R23_ROOT / "release_manifest.json"
    gt_path = (
        R23_ROOT
        / "myosim_runs"
        / "ground_truth"
        / "DB7-S21-ground_truth-postfix-v2"
        / "result.json"
    )
    decoder_path = (
        R23_ROOT / "myosim_runs" / "decoder" / "DB7-S21-decoder-postfix-v2" / "result.json"
    )

    if manifest_path.is_file() and gt_path.is_file() and decoder_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        ground_truth = json.loads(gt_path.read_text(encoding="utf-8"))
        real_decoder = json.loads(decoder_path.read_text(encoding="utf-8"))
        closure = manifest["closure"]
        episode = closure["functional_episode"]
        outcomes = closure["mujoco_results"]

        k1, k2, k3 = st.columns(3)
        k1.metric("Prediction artifacts", "33")
        row_count = sum(item["rows"] for group in manifest["datasets"].values() for item in group)
        k2.metric("Prediction rows/events", f"{row_count:,}")
        k3.metric("Shared DB7 S21 episode", f"{episode['window_count']} windows")
        st.caption(
            f"Frozen episode: windows {episode['window_start']}–{episode['window_end']} · "
            f"source SHA-256: {episode['source_prediction_sha256']}"
        )

        rows = []
        for label, result in (("Ground Truth", ground_truth), ("Real Decoder", real_decoder)):
            task = result["task_metrics"]
            rows.append(
                {
                    "Condition": label,
                    "Outcome": task["final_state"],
                    "Completion (s)": task["completion_time_s"],
                    "Final error (m)": task["final_error_m"],
                    "Grasp-stability steps": task["grasp_stability_steps"],
                    "Command corrections": task["command_corrections"],
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

        st.markdown("### What the comparison actually says")
        st.write(
            "Both conditions completed this same declared episode. The Real Decoder "
            "required substantially more command corrections and had much lower grasp "
            "stability than Ground Truth. Successful task completion here is evidence "
            "of downstream integration, not proof that the decoder is robust or ready "
            "for real-time or clinical use."
        )
        with st.expander("Full R2.3 closure manifest"):
            st.json(closure)
        st.download_button(
            "Download R2.3 release manifest",
            data=manifest_path.read_bytes(),
            file_name="r2_3_release_manifest.json",
            mime="application/json",
        )
        st.info(
            "Evidence boundary: recorded-data-derived offline replay through the MyoSim "
            "decision/control/safety stack and MuJoCo. No physical hardware, HIL, clinical "
            "validation, patient benefit, or real-time causal performance is established.",
            icon="ℹ️",
        )
    else:
        st.warning("Canonical R2.3 evidence files are not present in this deployment bundle.")


# --------------------------------------------------------------------------
# Tab: Hardware Twin (opt-in software-only actuator model)
# --------------------------------------------------------------------------

with tab_hardware_twin:
    st.subheader("Hardware Twin · actuator sensitivity experiment")
    st.write(
        "Run the same bundled intent replay through a software-only actuator layer "
        "before MuJoCo. This models assumptions; it does not connect to or validate "
        "physical hardware. The baseline tab remains unchanged."
    )
    delay_s = st.slider(
        "Command transport delay (s)",
        min_value=0.0,
        max_value=0.20,
        value=0.02,
        step=0.01,
    )
    fault_choice = st.selectbox(
        "Deterministic fault scenario",
        options=["none", FaultKind.COMMAND_DROPOUT.value, FaultKind.ACTUATOR_STUCK.value],
    )
    fault_start_s = st.slider(
        "Fault start (simulation seconds)",
        min_value=0.0,
        max_value=3.5,
        value=1.0,
        step=0.1,
    )
    fault_end_s = st.slider(
        "Fault end (simulation seconds)",
        min_value=0.1,
        max_value=3.5,
        value=1.5,
        step=0.1,
    )
    stuck_joint = st.selectbox(
        "Stuck actuator",
        options=["all actuators", "thumb_flex", "index_flex", "middle_flex", "ring_flex"],
    )
    st.caption(
        "Profiles are engineering assumptions for sensitivity analysis, not measured "
        "parameters. Compare task and control metrics together; one successful run "
        "is not a reliability claim."
    )
    if st.button("▶ Run Hardware Twin experiment", type="primary"):
        if fault_end_s <= fault_start_s:
            st.error("Fault end must be later than fault start.")
        else:
            faults: tuple[FaultWindow, ...] = ()
            if fault_choice != "none":
                faults = (
                    FaultWindow(
                        kind=FaultKind(fault_choice),
                        start_s=fault_start_s,
                        end_s=fault_end_s,
                        joint_name=(
                            None
                            if fault_choice == FaultKind.COMMAND_DROPOUT.value
                            or stuck_joint == "all actuators"
                            else stuck_joint
                        ),
                    ),
                )
            try:
                with st.spinner("Running the actuator-twin replay through MuJoCo..."):
                    st.session_state["hardware_twin"] = run_pick_place(
                        DEFAULT_REPLAY_PATH,
                        hardware_twin_delay_s=delay_s,
                        hardware_twin_faults=faults,
                    )
            except Exception as exc:  # noqa: BLE001 - surfaced for local diagnosis
                st.error(f"Hardware Twin run failed: {exc}")

    twin_payload = st.session_state.get("hardware_twin")
    if twin_payload is not None:
        twin_result: TaskRunResult = twin_payload["result"]
        twin_task = twin_result.task_metrics
        twin_control = twin_result.control_metrics
        cols = st.columns(4)
        cols[0].metric("Outcome", twin_task.final_state)
        cols[1].metric("Final error", f"{twin_task.final_error_m:.4f} m")
        cols[2].metric("Grasp stability", str(twin_task.grasp_stability_steps))
        cols[3].metric("Command corrections", str(twin_task.command_corrections))
        twin_evidence = twin_result.hardware_twin or {}
        trace = twin_result.hardware_twin_trace or ()
        if trace:
            profile_specs = twin_evidence.get("model_spec", {}).get("profiles", {})
            st.markdown("### Actuator response trace")
            unit_groups = (
                ("m", "Slide coordinates (m)"),
                ("rad", "Hinge coordinates (rad)"),
            )
            for unit, unit_label in unit_groups:
                joint_names = [
                    name
                    for name, profile in profile_specs.items()
                    if profile.get("coordinate_unit") == unit
                ]
                if not joint_names:
                    continue
                chart_data = {
                    "time_s": [point["timestamp_s"] for point in trace],
                    **{
                        name: [point["actuator_coordinates"].get(name) for point in trace]
                        for name in joint_names
                    },
                }
                st.caption(unit_label)
                st.line_chart(chart_data, x="time_s")

            st.markdown("### Command tracking error")
            error_groups = (("m", "Slide error (m)"), ("rad", "Hinge error (rad)"))
            for unit, unit_label in error_groups:
                joint_names = [
                    name
                    for name, profile in profile_specs.items()
                    if profile.get("coordinate_unit") == unit
                ]
                if not joint_names:
                    continue
                error_data = {
                    "time_s": [point["timestamp_s"] for point in trace],
                    **{
                        name: [point["tracking_error"].get(name) for point in trace]
                        for name in joint_names
                    },
                }
                st.caption(unit_label)
                st.line_chart(error_data, x="time_s")
        st.json(twin_evidence)
        with st.expander("Control metrics"):
            st.json(twin_control.to_dict())
        with st.expander("Run report"):
            st.markdown(twin_payload["report_md"])
        if twin_payload["clean_gif"] and twin_payload["debug_gif"]:
            twin_cols = st.columns(2)
            with twin_cols[0]:
                render_gif(twin_payload["clean_gif"], "Hardware Twin clean render")
            with twin_cols[1]:
                render_gif(twin_payload["debug_gif"], "Hardware Twin diagnostic render")


# --------------------------------------------------------------------------
# Tab: About
# --------------------------------------------------------------------------

with tab_about:
    st.subheader("About MyoSim")
    st.write(
        "MyoSim is a local-first, software-only research demonstrator for "
        "reproducible simulation of the path from motor-intent events to "
        "bounded virtual prosthetic action. The V1 implementation deliberately "
        "begins with synthetic and recorded intent replay — it does not "
        "require EMG devices, prosthetic hardware, patient-specific "
        "calibration, or live ML inference."
    )
    st.code(SYSTEM_CHAIN, language=None)
    st.markdown(
        "- **`src/myosim/control`** — confidence gating, temporal logic, state "
        "machine, safety limits, and motion targets.\n"
        "- **`src/myosim/simulation`** — physics-backend protocol/factory, "
        "MuJoCo (primary) and PyBullet (compatibility) backends.\n"
        "- **`src/myosim/hardware_twin`** — opt-in software actuator response and "
        "deterministic fault injection.\n"
        "- **`src/myosim/tasks`** — reach, grasp, and pick-and-place task "
        "definitions.\n"
        "- **`src/myosim/metrics` / `experiments`** — objective measures, "
        "reports, execution, and provenance."
    )
    st.info(
        "The virtual hand uses simplified geometric primitives and discrete "
        "pose targets — it is not an anatomical hand model or a validated "
        "biomechanics model. See `docs/limitations.md` for the full statement.",
        icon="📄",
    )
    if REPOSITORY_URL:
        st.markdown(
            f"Full documentation, source, licence (Apache-2.0), and citation "
            f"metadata are available at [{REPOSITORY_URL}]({REPOSITORY_URL})."
        )
    else:
        st.caption(
            "Set MYOSIM_REPOSITORY_URL when publishing this release to expose "
            "its canonical source link."
        )
