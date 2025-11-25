import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

def plot_radar(scores: dict):
    metrics = [
        "Safety", "Health", "Education", "EconomicOpportunity",
        "HousingAffordability", "DigitalAccess", "Environment", "Accessibility"
    ]

    values = [scores[m] for m in metrics]
    
    # Radar charts must end with same value to close loop
    values += values[:1]
    
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True))

    # Draw labels + lines
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics)

    ax.set_ylim(0, 100)
    ax.plot(angles, values, linewidth=2, linestyle='solid')
    ax.fill(angles, values, alpha=0.25)

    st.pyplot(fig)
