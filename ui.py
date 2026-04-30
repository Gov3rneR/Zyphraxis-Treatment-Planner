"""
ui.py - Streamlit browser interface for Zyphraxis.

Run:
    streamlit run ui.py

Requires the API to be running at API_URL (default: http://localhost:8000).
"""
from __future__ import annotations

import json
import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Zyphraxis",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("ZYPHRAXIS_API_KEY", "zyphraxis-demo-key")


@st.cache_data(ttl=60)
def load_scenarios() -> list[dict]:
    try:
        resp = requests.get(f"{API_URL}/scenarios", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        try:
            with open("scenarios.json") as fh:
                return json.load(fh)
        except FileNotFoundError:
            return []


st.title("🧬 Zyphraxis Treatment Planner")
st.caption("AI-driven personalised treatment sequencing · For research use only")

try:
    health = requests.get(f"{API_URL}/health", timeout=3)
    if health.status_code == 200:
        st.success(f"✅ API connected — {API_URL}", icon="🟢")
    else:
        st.warning("⚠️ API reachable but returned non-200", icon="🟡")
except Exception:
    st.error(f"❌ Cannot reach API at {API_URL}. Start with: uvicorn main:app --reload", icon="🔴")

st.sidebar.header("📄 Demo Scenarios")
scenarios      = load_scenarios()
scenario_names = ["Custom"] + [s["name"] for s in scenarios]
selected_name  = st.sidebar.selectbox("Load preset case", scenario_names)

if selected_name != "Custom":
    scenario = next(s for s in scenarios if s["name"] == selected_name)
    st.sidebar.info(scenario.get("description", ""))
    defaults = scenario
else:
    defaults = {"tumor_escape_h": 960, "max_risk": 0.25, "human_use": True, "mode": "balanced"}

st.sidebar.markdown("---")
st.sidebar.caption("Zyphraxis v1.0 | Research use only")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Patient Parameters")
    tumor_escape_h = st.number_input(
        "Tumour Escape Time (hours)",
        min_value=24, max_value=8_760,
        value=int(defaults.get("tumor_escape_h", 960)), step=24,
        help="Estimated hours until the tumour escapes the current treatment window.",
    )
    max_risk = st.slider(
        "Maximum Acceptable Risk", 0.0, 1.0,
        float(defaults.get("max_risk", 0.25)), 0.01,
        help="0 = zero risk tolerance, 1 = maximum risk accepted.",
    )

with col2:
    st.subheader("Constraints")
    human_use = st.checkbox(
        "Human trials allowed",
        value=bool(defaults.get("human_use", True)),
        help="Uncheck for patients ineligible for experimental treatments.",
    )
    mode = st.selectbox(
        "Optimisation Mode",
        ["aggressive", "balanced", "conservative"],
        index=["aggressive", "balanced", "conservative"].index(defaults.get("mode", "balanced")),
        help="Aggressive = minimise time; Conservative = minimise risk.",
    )
    patient_id = st.text_input("Patient ID (optional, for logging only)", "")

if st.button("🚀 Generate Plan", type="primary", use_container_width=True):
    payload = {
        "tumor_escape_h": tumor_escape_h,
        "max_risk":       max_risk,
        "human_use":      human_use,
        "mode":           mode,
        "patient_id":     patient_id or None,
    }

    with st.spinner("Running Zyphraxis brain…"):
        try:
            resp = requests.post(
                f"{API_URL}/generate_plan",
                json=payload,
                headers={"X-API-Key": API_KEY},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot reach the API.")
            st.code("uvicorn main:app --reload", language="bash")
            st.stop()
        except requests.exceptions.HTTPError as exc:
            st.error(f"API returned an error: {exc.response.status_code}")
            st.json(exc.response.json())
            st.stop()
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            st.stop()

    if data.get("status") in ("NO_PATH", "INVALID_INPUT"):
        st.error("⚠️ No viable treatment plan found under these constraints.")
        st.warning(data.get("explanation", "No explanation returned."))
        st.info("Try: increasing the risk budget, extending the escape window, or enabling human trials.")
    else:
        st.success("✅ Plan Generated Successfully")

        m = data.get("metrics") or {}
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Time",     f"{m.get('total_time_h', 0):.0f} hrs")
        c2.metric("Risk Score",     f"{m.get('risk_score', 0):.1%}")
        c3.metric("Est. Cost",      f"${m.get('estimated_cost', 0):,.0f}")
        c4.metric("HLA Mismatches", str(m.get("hla_mismatches", 0)))
        c5.metric("Confidence",     f"{m.get('confidence', 0):.0%}")

        st.subheader("Treatment Sequence")
        plan_df = pd.DataFrame(data.get("plan", []))
        if not plan_df.empty:
            st.dataframe(plan_df, use_container_width=True, hide_index=True)

        st.subheader("Clinical Explanation")
        st.info(data.get("explanation", "—"))

        alts = data.get("alternatives", 0)
        if alts:
            st.caption(f"ℹ️ {alts} alternative plan(s) also within constraints.")

        filename = (
            f"zyphraxis_{patient_id or 'report'}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        st.download_button(
            "📥 Download Report (JSON)",
            json.dumps(data, indent=2),
            file_name=filename,
            mime="application/json",
        )

        with st.expander("Raw API response"):
            st.json(data)
