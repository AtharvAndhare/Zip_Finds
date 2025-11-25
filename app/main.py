# app/main.py


import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


import streamlit as st

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


def main():
    st.set_page_config(page_title="Civic Intelligence AI", layout="wide")

    st.title("🏙️ Zip Finds AI - Your AI-Powered ZIP Code Analyzer(Python, Data-Driven)")

    # Initialize session state the first time the app loads
    if "raw_data" not in st.session_state:
        st.session_state.raw_data = None
        st.session_state.scores = None
        st.session_state.computed_scores = None
        st.session_state.selected_zip = None
        st.session_state.selected_persona = default_persona()

    with st.sidebar:
        st.header("Input ZIP")
        zip_code_input = st.text_input("ZIP Code (US)", value=st.session_state.selected_zip or "07306")
        persona = st.selectbox("Persona", PERSONAS, index=PERSONAS.index(st.session_state.selected_persona))

        run = st.button("Analyze ZIP")

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

    # Debug section: only show raw data if needed
    st.subheader("🔍 RAW API Data Debug")
    with st.expander("Raw Data (Click to expand)", expanded=False):
        st.json(raw_data)

    # Layout
    col1, col2 = st.columns([1.4, 1])

    with col1:
        st.subheader("📊 Scorecard")

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

    with st.spinner("Generating narrative and recommendations..."):
        narrative = generate_narrative(zip_code, scores, persona)

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
