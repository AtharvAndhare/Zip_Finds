# app/main.py

import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st

# Redirect to new site
st.markdown(
    '<meta http-equiv="refresh" content="0; url=https://zipfinds.vercel.app/">',
    unsafe_allow_html=True
)
st.markdown("Redirecting to [zipfinds.vercel.app](https://zipfinds.vercel.app/)...")
st.stop()

from config.settings import settings
from data_sources.zip_validator import is_valid_us_zip, normalize_zip
from core.aggregator import collect_all_data
from core.scoring_engine import compute_scores
#from visualizations.radar_chart import plot_radar
from visualizations.radial_chart import plot_radial
from visualizations.score_cards import render_scorecard
from visualizations.map_view import make_map_df
from llm.narrative_generator import generate_narrative
from app.personas import PERSONAS, default_persona
from app.chatbot import answer_followup


def _render_data_cards(raw_data: dict, zip_code: str):
    """Render extracted data as a Census-Bureau-style card grid."""
    import streamlit.components.v1 as components

    census = raw_data.get("census", {}) or {}
    housing_data = raw_data.get("housing", {}) or {}
    broadband = raw_data.get("broadband", {}) or {}
    crime = raw_data.get("crime", {}) or {}
    health = raw_data.get("health", {}) or {}
    osm = raw_data.get("osm", {}) or {}
    air = raw_data.get("air_quality", {}) or {}

    def _fmt(v, prefix="", suffix="", decimals=0):
        if v is None:
            return "N/A"
        try:
            v = float(v)
        except (ValueError, TypeError):
            return str(v)
        if decimals == 0:
            return f"{prefix}{v:,.0f}{suffix}"
        return f"{prefix}{v:,.{decimals}f}{suffix}"

    pop = census.get("resident_base")
    income = census.get("median_income")
    bach = census.get("bachelors_rate")
    rent = housing_data.get("median_rent")
    rent_ratio = housing_data.get("rent_to_income")
    bb_pct = broadband.get("broadband_pct")
    fiber = broadband.get("fiber_pct")
    cable = broadband.get("cable_pct")
    hospitals_n = health.get("hospitals", 0)
    hpsa = health.get("is_hpsa", False)
    crime_rate = crime.get("crime_per_1k")
    parks = osm.get("parks", 0)
    transit = osm.get("transit_stops", 0)
    grocery = osm.get("grocery_stores", 0)
    aqi_val = air.get("aqi")
    aqi_cat = air.get("category", "N/A")

    if crime_rate is not None:
        crime_level = "Low" if crime_rate < 30 else "Moderate" if crime_rate < 60 else "High"
    else:
        crime_level = ""

    rent_sub = "Median Rent"
    if rent_ratio:
        rent_sub += f" &nbsp;|&nbsp; Rent-to-Income: {rent_ratio*100:.1f}%"

    bb_sub = "Broadband Coverage"
    if fiber and cable:
        bb_sub = f"Fiber: {fiber:.1f}% &nbsp;|&nbsp; Cable: {cable:.1f}%"

    safety_sub = "Crime Proxy Score"
    if crime_level:
        safety_sub += f" &nbsp;|&nbsp; Level: {crime_level}"

    cards = [
        ("&#x1F465;", "Population &amp; People",  "Total Population",                          _fmt(pop),                                       "US Census ACS 5-Year Estimates"),
        ("&#x1F4B0;", "Income &amp; Economy",      "Median Household Income",                   _fmt(income, prefix="$"),                        "US Census ACS 5-Year Estimates"),
        ("&#x1F393;", "Education",                  "Bachelor&#39;s Degree or Higher",           _fmt(bach, suffix="%", decimals=1),              "US Census ACS 5-Year Estimates"),
        ("&#x1F3E0;", "Housing",                    rent_sub,                                    _fmt(rent, prefix="$"),                          "US Census ACS 5-Year Estimates"),
        ("&#x1F4F6;", "Digital Access",             bb_sub,                                      _fmt(bb_pct, suffix="%", decimals=1),            "US Census ACS Broadband Data"),
        ("&#x1F3E5;", "Health &amp; Care",          f"Hospitals: {hospitals_n} &nbsp;|&nbsp; HPSA: {'Yes' if hpsa else 'No'}",  f"{hospitals_n} Hospitals",   "HRSA / OpenStreetMap"),
        ("&#x1F6E1;", "Safety",                     safety_sub,                                  _fmt(crime_rate, decimals=1) if crime_rate is not None else "N/A",  "Computed from Census &amp; OSM"),
        ("&#x1F333;", "Points of Interest",         f"Transit: {transit} &nbsp;|&nbsp; Grocery: {grocery}",  f"{parks} Parks",                   "OpenStreetMap Overpass API"),
        ("&#x1F32C;", "Environment",                f"Air Quality Index &nbsp;|&nbsp; {aqi_cat}",  str(aqi_val if aqi_val is not None else "N/A"),  "AirNow EPA API"),
    ]

    # Build card HTML snippets
    card_blocks = ""
    for emoji, title, subtitle, value, source in cards:
        card_blocks += f"""
        <div class="dc">
            <div class="dc-icon">{emoji}</div>
            <div class="dc-body">
                <div class="dc-title">{title}</div>
                <div class="dc-value">{value}</div>
                <div class="dc-sub">{subtitle}</div>
                <div class="dc-src">{source}</div>
            </div>
        </div>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: transparent;
        }}
        .header {{
            color: #c0c8d8;
            font-size: 14px;
            margin-bottom: 16px;
            letter-spacing: 0.3px;
        }}
        .header span {{
            color: #ffffff;
            font-weight: 600;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
        }}
        .dc {{
            background: linear-gradient(135deg, #1a1f36 0%, #252b48 100%);
            border: 1px solid #333a56;
            border-radius: 10px;
            padding: 18px 20px;
            display: flex;
            align-items: flex-start;
            gap: 14px;
            transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
        }}
        .dc:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 24px rgba(0,0,0,0.4);
            border-color: #4e7cff;
        }}
        .dc-icon {{
            flex-shrink: 0;
            width: 46px;
            height: 46px;
            background: rgba(78,124,255,0.12);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
        }}
        .dc-body {{
            flex: 1;
            min-width: 0;
        }}
        .dc-title {{
            font-size: 11.5px;
            font-weight: 600;
            color: #8a94a6;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 4px;
        }}
        .dc-value {{
            font-size: 26px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.15;
            margin-bottom: 5px;
        }}
        .dc-sub {{
            font-size: 12px;
            color: #6b7588;
            margin-bottom: 10px;
            line-height: 1.4;
        }}
        .dc-src {{
            font-size: 10.5px;
            color: #4a5264;
            border-top: 1px solid rgba(255,255,255,0.06);
            padding-top: 8px;
        }}
    </style>
    </head>
    <body>
        <div class="header">United States &nbsp;/&nbsp; ZCTA5 <span>{zip_code}</span> &nbsp;&mdash;&nbsp; Raw Data Values</div>
        <div class="grid">
            {card_blocks}
        </div>
    </body>
    </html>
    """

    components.html(html, height=520, scrolling=False)
    st.markdown("---")


def main():
    st.set_page_config(page_title="Zip Finds AI", layout="wide")

    st.title("🏙️ Zip Finds AI - Your AI-Powered ZIP Code Analyzer(Python, Data-Driven)")

    # Initialize session state the first time the app loads
    if "raw_data" not in st.session_state:
        st.session_state.raw_data = None
        st.session_state.scores = None
        st.session_state.computed_scores = None
        st.session_state.selected_zip = None
        st.session_state.selected_persona = default_persona()
    if "zip_input" not in st.session_state:
        st.session_state.zip_input = ""

    with st.sidebar:
        st.header("Input ZIP")
        with st.form("zip_form"):
            zip_code_input = st.text_input("ZIP Code (US)", key="zip_input")
            persona = st.selectbox("Persona", PERSONAS, index=PERSONAS.index(st.session_state.selected_persona))
            run = st.form_submit_button("Analyze ZIP")

        st.markdown("---")
        st.caption(
            f"Mode: {'Mock data' if settings.USE_MOCK_DATA else 'Live APIs'} · "
            f"LLM: {settings.LLM_PROVIDER}"
        )

    # Keep persona in session state so it's available for other components
    st.session_state.selected_persona = persona

    if run:
        normalized_zip = normalize_zip(zip_code_input)
        if not is_valid_us_zip(normalized_zip):
            st.error("Please enter a valid 5-digit US ZIP code.")
            st.stop()

        with st.spinner("Collecting data sources and computing scores..."):
            raw_data = collect_all_data(normalized_zip)
            scores = compute_scores(raw_data)

        st.session_state.raw_data = raw_data
        st.session_state.scores = scores
        st.session_state.computed_scores = scores  # default until UI recalculates
        st.session_state.selected_zip = normalized_zip

    if st.session_state.raw_data is None or st.session_state.scores is None:
        st.info("Enter a ZIP and click **Analyze ZIP** to start.")
        return

    raw_data = st.session_state.raw_data
    scores = st.session_state.scores
    zip_code = st.session_state.selected_zip
    persona = st.session_state.selected_persona

    # ===========================================
    # RAW VALUES SECTION - Census-style card grid
    # ===========================================
    _render_data_cards(raw_data, zip_code)

    # Debug section (collapsed)
    with st.expander("Raw JSON Data (Debug)", expanded=False):
        st.json(raw_data)

    # Layout
    col1, col2 = st.columns([1.4, 1])

    with col1:
        st.subheader("Civic Scores (0-100)")

        # Use the scorecard component that computes and displays dynamic values
        computed_scores = render_scorecard(scores, raw_data, zip_code)
        st.session_state.computed_scores = computed_scores

        # Extract metric scores for the radial chart (exclude overall)
        metric_scores_for_chart = {k: v for k, v in computed_scores.items() if k != "OverallCivicScore"}

        fig = plot_radial(metric_scores_for_chart)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🗺️ Location")
        map_df = make_map_df(zip_code)
        st.map(map_df, zoom=11)

    st.markdown("---")

    # Use the correctly computed scores for narrative (from scorecard recomputation)
    final_scores = st.session_state.get("computed_scores") or scores

    with st.spinner("Generating narrative and recommendations..."):
        narrative = generate_narrative(zip_code, final_scores, persona)

    st.subheader("🧠 Narrative & Recommendations")
    st.markdown(narrative)

    st.markdown("---")
    st.subheader("💬 Chatbot")
    followup = st.text_area(
        "Ask a follow-up question about this ZIP:",
        placeholder="e.g., How suitable is this area for a tech startup?",
    )
    if st.button("Send Question"):
        if followup.strip():
            with st.spinner("Thinking..."):
                latest_scores = st.session_state.get("computed_scores") or scores
                reply = answer_followup(zip_code, persona, latest_scores, followup.strip())
            st.markdown("**Chatbot:**")
            st.markdown(reply)
        else:
            st.warning("Please type a question first.")


if __name__ == "__main__":
    main()
