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
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from myosim import __version__
from myosim.core.config import load_config
from myosim.core.errors import MyoSimError
from myosim.experiments.basic_task_runner import run_grasp_evaluation, run_reach_evaluation
from myosim.experiments.task_runner import PickPlaceExperimentRunner, TaskRunResult
from myosim.metrics.reporting import write_task_markdown_report
from myosim.rendering.overlays import DebugOverlay
from myosim.rendering.recorder import FrameRecorder
from myosim.runtime import resource_root
from myosim.signals.replay import CsvIntentReplay
from myosim.simulation.factory import backend_status, create_backend

# TODO: point this at your published repository once it exists on GitHub.
GITHUB_REPO_URL = "https://github.com/<your-username>/myosim"

REPO_ROOT = resource_root()
DEMO_CONFIG_PATH = REPO_ROOT / "configs" / "demo.yaml"
REACH_CONFIG_PATH = REPO_ROOT / "configs" / "tasks" / "reach.yaml"
GRASP_CONFIG_PATH = REPO_ROOT / "configs" / "tasks" / "grasp.yaml"
DEFAULT_REPLAY_PATH = REPO_ROOT / "examples" / "intents" / "pick_place_replay.csv"
HAND_MODEL_PATH = REPO_ROOT / "assets" / "models" / "hand.xml"

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


def run_pick_place(replay_path: Path) -> dict[str, Any]:
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
                intent=event.label.value,
                confidence=event.confidence,
                controller_state=control.state_output.state.value,
                task_state=task_step.state.value,
                joint_targets_rad=control.targets.positions_rad,
            )
        )

    result: TaskRunResult = PickPlaceExperimentRunner(config, REPO_ROOT).run(
        source, on_step=on_step
    )

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
    st.markdown(f"[Source code on GitHub]({GITHUB_REPO_URL})")
    st.markdown("Licence: Apache-2.0 · Cite via `CITATION.cff`")
    st.divider()
    st.caption(
        "This demo mirrors the `myosim` CLI exactly — it calls the same "
        "public runners and adds no new simulation, control, or safety logic."
    )

tab_pick_place, tab_reach_grasp, tab_environment, tab_about = st.tabs(
    ["🤖 Pick & place", "🎯 Reach & grasp", "🩺 Environment status", "ℹ️ About"]
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
    st.markdown(
        f"Full documentation, source, licence (Apache-2.0), and citation "
        f"metadata live in the repository: [{GITHUB_REPO_URL}]({GITHUB_REPO_URL})"
    )
