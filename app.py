"""
Multimodal Construction Intelligence Platform
Skill Wallet Capstone Project 1 — Streamlit edition.

Run:  streamlit run app.py
"""
from __future__ import annotations

import io
import json
import re
import urllib.parse
from typing import Any, Dict, List, Optional

import streamlit as st
from PIL import Image

try:
    import google.generativeai as genai
except ImportError:  # app still runs in demo mode
    genai = None

st.set_page_config(page_title="Construction Intelligence Platform", page_icon="🏗️", layout="wide")

# --------------------------------------------------------------------------- styling
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono&display=swap');
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
.stApp { background: #1c1a17; color: #f3efe6; }
.hazard { height: 6px; background: repeating-linear-gradient(-45deg,#f5c518 0 12px,#1c1a17 12px 24px); margin-bottom: 1rem; }
.metric-card { background:#26231f; border:1px solid #3a362f; border-radius:10px; padding:16px; }
.metric-card .lbl { font-family:'JetBrains Mono'; font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:#a8a092; }
.metric-card .val { font-size:26px; font-weight:700; margin-top:6px; }
.pill { display:inline-block; padding:2px 10px; border-radius:999px; font-family:'JetBrains Mono'; font-size:12px; }
.good { background:rgba(70,190,120,.15); color:#5fd38d; }
.warn { background:rgba(245,170,40,.15); color:#f5b440; }
.bad  { background:rgba(230,70,60,.15); color:#ff6a5e; }
.neutral { background:#33302a; color:#f3efe6; }
.kicker { font-family:'JetBrains Mono'; color:#f5c518; letter-spacing:.3em; font-size:12px; text-transform:uppercase; }
</style>
<div class="hazard"></div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- JSON contracts (prompts)
PPE_PROMPT = """You are a certified construction safety auditor (OSHA 1926 and IS 456 / BOCW Act).
Audit the site photo for PPE compliance and hazards. Reply with ONLY JSON:
{"safety_score": 0-100, "overall_status": "Compliant|Needs Attention|Non-Compliant|Critical",
 "workers_detected": int, "summary": str,
 "ppe_detection": {"helmet": {"status": "Detected|Missing|Partial|Not Visible", "note": str},
   "high_vis_vest": {...}, "steel_toe_boots": {...}, "safety_harness": {...}},
 "hazards": [{"hazard": str, "severity": "Low|Medium|High|Critical", "standard": str, "remedy": str}]}"""

CRACK_PROMPT = """You are a senior structural engineer (IS 456:2000, IS 13311). Classify the concrete defect.
Reply with ONLY JSON:
{"defect_type": "Hairline|Settlement|Structural Shear|Thermal Expansion|Spalling|No Defect",
 "severity_score": 0-10, "estimated_width_mm": float, "pattern": str,
 "urgency": "Monitor|Repair within 3 months|Repair within 2 weeks|Immediate",
 "structural_risk": "Cosmetic|Moderate|Severe", "summary": str, "root_causes": [str],
 "recommended_repairs": [{"method": str, "detail": str}], "monitoring": str}"""

DEMO_PPE = {
    "safety_score": 68, "overall_status": "Needs Attention", "workers_detected": 4,
    "summary": "DEMO MODE — sample audit. Add a Gemini API key for live analysis.",
    "ppe_detection": {
        "helmet": {"status": "Detected", "note": "4/4 workers wearing hard hats"},
        "high_vis_vest": {"status": "Partial", "note": "1 worker without vest"},
        "steel_toe_boots": {"status": "Not Visible", "note": "Feet obscured by debris"},
        "safety_harness": {"status": "Missing", "note": "Worker on scaffold edge without harness"},
    },
    "hazards": [
        {"hazard": "Unprotected edge at level 2", "severity": "Critical", "standard": "OSHA 1926.501", "remedy": "Install guardrails and enforce full-body harness"},
        {"hazard": "Loose rebar ends", "severity": "Medium", "standard": "OSHA 1926.701(b)", "remedy": "Fit rebar caps"},
    ],
}
DEMO_CRACK = {
    "defect_type": "Settlement", "severity_score": 6, "estimated_width_mm": 1.8, "pattern": "Diagonal stepped",
    "urgency": "Repair within 2 weeks", "structural_risk": "Moderate",
    "summary": "DEMO MODE — sample diagnosis. Add a Gemini API key for live analysis.",
    "root_causes": ["Differential foundation settlement", "Poor soil compaction"],
    "recommended_repairs": [
        {"method": "Epoxy injection", "detail": "Low-viscosity epoxy at 200 mm port spacing"},
        {"method": "Structural re-grouting", "detail": "Pressure-grout foundation voids with non-shrink grout"},
    ],
    "monitoring": "Install tell-tale gauges and log weekly for 8 weeks.",
}

# --------------------------------------------------------------------------- AI helpers
def get_model(api_key: str):
    if not api_key or genai is None:
        return None
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as exc:  # noqa: BLE001
        st.sidebar.error(f"Gemini init failed: {exc}")
        return None


def parse_json(text: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("Model did not return JSON")
    return json.loads(match.group(0))


def vision_report(model, prompt: str, image: Image.Image, demo: Dict[str, Any]) -> Dict[str, Any]:
    if model is None:
        return demo
    try:
        resp = model.generate_content([prompt, image])
        return parse_json(resp.text)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Analysis failed ({exc}). Showing demo report instead.")
        return demo


def tone(value: str) -> str:
    v = str(value).lower()
    if re.search(r"critical|non-compliant|missing|immediate|severe|high", v):
        return "bad"
    if re.search(r"medium|partial|attention|moderate|weeks|not visible|months", v):
        return "warn"
    if re.search(r"low|detected|compliant|monitor|cosmetic|no defect", v):
        return "good"
    return "neutral"


def pill(text: str) -> str:
    return f'<span class="pill {tone(text)}">{text}</span>'


def metric(col, label: str, value: str) -> None:
    col.markdown(f'<div class="metric-card"><div class="lbl">{label}</div><div class="val">{value}</div></div>', unsafe_allow_html=True)


def load_image(upload) -> Optional[Image.Image]:
    try:
        return Image.open(io.BytesIO(upload.getvalue())).convert("RGB")
    except Exception:  # noqa: BLE001
        st.error("Could not read that image. Please upload a JPG or PNG.")
        return None

# --------------------------------------------------------------------------- valuation engine
STRUCTURES = {
    "Residential": dict(cost=1800, market=1.0, steel=4.0, cement=0.40),
    "Commercial": dict(cost=2400, market=1.3, steel=5.0, cement=0.45),
    "Industrial": dict(cost=2100, market=0.8, steel=6.0, cement=0.50),
    "Villa": dict(cost=2800, market=1.2, steel=4.5, cement=0.42),
}
TIERS = {"Tier 1": dict(mult=1.35, rate=12000), "Tier 2": dict(mult=1.10, rate=6000), "Tier 3": dict(mult=0.90, rate=3500)}


def valuate(structure: str, sqft: float, tier: str, completion: int) -> Dict[str, float]:
    s, t = STRUCTURES[structure], TIERS[tier]
    pct = max(0, min(completion, 100)) / 100
    budget = sqft * s["cost"] * t["mult"]
    return dict(
        budget=budget, capex=budget * pct, remaining=budget * (1 - pct),
        market=sqft * t["rate"] * s["market"] * (0.4 + 0.6 * pct),
        steel=sqft * s["steel"] / 1000, cement=round(sqft * s["cement"]),
    )


def inr(n: float) -> str:
    if n >= 1e7:
        return f"₹{n / 1e7:.2f} Cr"
    if n >= 1e5:
        return f"₹{n / 1e5:.2f} L"
    return f"₹{n:,.0f}"


def milestone(c: int) -> str:
    return ("Site prep & foundation" if c < 15 else "Superstructure / RCC frame" if c < 40 else
            "Masonry & MEP rough-in" if c < 65 else "Finishing & façade" if c < 90 else "Handover & snagging")

# --------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown('<p class="kicker">Capstone 01</p>', unsafe_allow_html=True)
    st.title("🏗️ Construction Intelligence")
    api_key = st.text_input("Google Gemini API key", type="password", help="Leave blank for demo mode")
    model = get_model(api_key)
    st.markdown(pill("LIVE · Gemini 1.5") if model else pill("DEMO MODE"), unsafe_allow_html=True)
    st.markdown("### Architecture")
    st.markdown(
        "- **Vision:** Gemini 1.5 multimodal → JSON contracts\n"
        "- **Valuation:** deterministic INR cost engine\n"
        "- **Rendering:** Pollinations / Flux\n"
        "- **Assistant:** multi-turn Gemini chat\n"
        "- **Storage:** none (session state only)"
    )
    st.markdown("### Features\n1. Site Safety & PPE\n2. Crack Diagnostics\n3. Planning & Valuation\n4. Site Assistant")

st.markdown('<p class="kicker">Skill Wallet · Capstone 01</p>', unsafe_allow_html=True)
st.title("Multimodal Construction Intelligence Platform")
tab1, tab2, tab3, tab4 = st.tabs(["🦺 Safety & PPE", "🧱 Crack Diagnostics", "🏢 Planning & Valuation", "🌦️ Site Assistant"])

# --------------------------------------------------------------------------- tab 1
with tab1:
    up = st.file_uploader("Construction site photo", type=["jpg", "jpeg", "png"], key="ppe")
    if up and (img := load_image(up)):
        left, right = st.columns([2, 3])
        left.image(img, use_container_width=True)
        if left.button("Run PPE safety audit", type="primary"):
            with st.spinner("Auditing PPE compliance…"):
                st.session_state.ppe = vision_report(model, PPE_PROMPT, img, DEMO_PPE)
        rep = st.session_state.get("ppe")
        if rep:
            with right:
                c1, c2, c3 = st.columns(3)
                metric(c1, "Safety score", f"{rep.get('safety_score', 0)}/100")
                metric(c2, "Status", pill(rep.get("overall_status", "-")))
                metric(c3, "Workers", str(rep.get("workers_detected", "-")))
                st.caption(rep.get("summary", ""))
                st.subheader("PPE checklist")
                for k, v in rep.get("ppe_detection", {}).items():
                    st.markdown(f"**{k.replace('_', ' ').title()}** {pill(v.get('status', ''))} — {v.get('note', '')}", unsafe_allow_html=True)
                st.subheader("Hazards")
                for h in rep.get("hazards", []):
                    st.markdown(f"**{h['hazard']}** {pill(h['severity'])} `{h.get('standard', '')}`<br>→ {h['remedy']}", unsafe_allow_html=True)
                st.download_button("⬇ Download JSON report", json.dumps(rep, indent=2), "ppe-safety-report.json", "application/json")

# --------------------------------------------------------------------------- tab 2
with tab2:
    up = st.file_uploader("Concrete / wall surface photo", type=["jpg", "jpeg", "png"], key="crack")
    if up and (img := load_image(up)):
        left, right = st.columns([2, 3])
        left.image(img, use_container_width=True)
        if left.button("Diagnose crack", type="primary"):
            with st.spinner("Running structural diagnostics…"):
                st.session_state.crack = vision_report(model, CRACK_PROMPT, img, DEMO_CRACK)
        rep = st.session_state.get("crack")
        if rep:
            with right:
                c1, c2, c3 = st.columns(3)
                metric(c1, "Defect", rep.get("defect_type", "-"))
                metric(c2, "Width", f"{rep.get('estimated_width_mm', 0)} mm")
                metric(c3, "Severity", f"{rep.get('severity_score', 0)}/10")
                st.progress(min(int(float(rep.get("severity_score", 0)) * 10), 100))
                st.markdown(f"{pill(rep.get('urgency', ''))} {pill('Risk: ' + rep.get('structural_risk', ''))}", unsafe_allow_html=True)
                st.write(rep.get("summary", ""))
                a, b = st.columns(2)
                a.subheader("Root causes")
                for c in rep.get("root_causes", []):
                    a.markdown(f"- {c}")
                b.subheader("Repairs")
                for r in rep.get("recommended_repairs", []):
                    b.markdown(f"**{r['method']}** — {r['detail']}")
                st.caption(f"Monitoring: {rep.get('monitoring', '')}")
                st.download_button("⬇ Download JSON report", json.dumps(rep, indent=2), "crack-report.json", "application/json")

# --------------------------------------------------------------------------- tab 3
with tab3:
    left, right = st.columns([2, 3])
    with left:
        structure = st.selectbox("Structure type", list(STRUCTURES))
        sqft = st.number_input("Built-up area (sqft)", min_value=100, value=2500, step=100)
        tier = st.selectbox("Location tier", list(TIERS))
        completion = st.slider("Completion %", 0, 100, 45)
    v = valuate(structure, sqft, tier, completion)
    with right:
        r1 = st.columns(3)
        metric(r1[0], "Total budget", inr(v["budget"]))
        metric(r1[1], "Capex incurred", inr(v["capex"]))
        metric(r1[2], "Market valuation", inr(v["market"]))
        r2 = st.columns(3)
        metric(r2[0], "Balance", inr(v["remaining"]))
        metric(r2[1], "Steel (TMT)", f"{v['steel']:.1f} t")
        metric(r2[2], "Cement bags", f"{v['cement']:,}")
        st.markdown("#### Milestone progress")
        st.progress(completion / 100)
        st.caption(f"Current phase: {milestone(completion)}")
        prompt = f"Photorealistic 3D architectural rendering of a modern {structure.lower()} building, {sqft} sqft, Indian {tier} city, golden hour, high detail"
        st.code(prompt, language=None)
        if st.button("Generate conceptual 3D rendering"):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=576&nologo=true"
            st.image(url, caption="Pollinations / Flux concept render", use_container_width=True)
    st.caption("Indicative 2026 Indian benchmark rates — planning use only.")

# --------------------------------------------------------------------------- tab 4
WEATHER: Dict[str, List[tuple]] = {
    "Normal": [("Low", "Standard ops. Toolbox talk + PPE check at shift start."), ("Low", "Wet-cure fresh concrete ≥ 7 days (IS 456).")],
    "High Wind": [("Critical", "Suspend tower crane & hoist lifts above 40 km/h."), ("High", "Secure sheets, formwork panels, scaffold netting."), ("High", "Double-lanyard harness for all work at height.")],
    "Heavy Rain": [("Critical", "Isolate temporary DBs; RCCB/ELCB + IP65 enclosures."), ("High", "Stop concreting; cover fresh pours."), ("Medium", "Dewater excavations; inspect trench shoring.")],
    "Extreme Heat": [("High", "Heavy work before 11am / after 4pm; water + ORS breaks."), ("High", "Chilled mix water; concrete < 32°C at placing."), ("Medium", "Start curing immediately to stop plastic shrinkage.")],
}

with tab4:
    left, right = st.columns([2, 3])
    with left:
        weather = st.radio("Today's site weather", list(WEATHER), horizontal=True)
        for sev, text in WEATHER[weather]:
            st.markdown(f"{pill(sev)} {text}", unsafe_allow_html=True)
    with right:
        st.subheader("SiteMind engineering assistant")
        st.session_state.setdefault("chat", [])
        for m in st.session_state.chat:
            st.chat_message(m["role"]).write(m["content"])
        if q := st.chat_input("Ask about curing, mix design, IS codes, safety…"):
            st.session_state.chat.append({"role": "user", "content": q})
            st.chat_message("user").write(q)
            system = f"You are SiteMind, a concise construction engineering assistant for Indian sites. Weather today: {weather}. Cite IS codes/OSHA; use INR."
            if model is None:
                answer = f"(Demo mode) Under **{weather}** conditions: " + WEATHER[weather][0][1] + " Add a Gemini key for full answers."
            else:
                try:
                    history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in st.session_state.chat[:-1]]
                    chat = model.start_chat(history=[{"role": "user", "parts": [system]}, {"role": "model", "parts": ["Understood."]}] + history)
                    answer = chat.send_message(q).text
                except Exception as exc:  # noqa: BLE001
                    answer = f"Assistant error: {exc}"
            st.session_state.chat.append({"role": "assistant", "content": answer})
            st.chat_message("assistant").write(answer)
