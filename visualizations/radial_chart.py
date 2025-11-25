# visualizations/radial_chart.py

import streamlit as st
import plotly.graph_objects as go

def plot_radial(scores: dict):
    # Remove OverallCivicScore because we plot only metrics
    data = {k: v for k, v in scores.items() if k != "OverallCivicScore"}

    labels = list(data.keys())
    values = list(data.values())

    # Create subplots in a 2x4 grid
    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=2, cols=4,
        subplot_titles=labels,
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )

    for i, (label, value) in enumerate(zip(labels, values)):
        row = (i // 4) + 1
        col = (i % 4) + 1
        
        # Add background bars first (they'll be behind the value bar)
        # White background (0-33)
        fig.add_trace(
            go.Bar(
                x=[label],
                y=[33],
                orientation='v',
                marker=dict(color='#FFFFFF', line=dict(width=0)),
                showlegend=False,
                hoverinfo='skip'
            ),
            row=row, col=col
        )
        
        # Powder blue background (33-66)
        fig.add_trace(
            go.Bar(
                x=[label],
                y=[33],  # Height of this segment
                base=33,
                orientation='v',
                marker=dict(color='#B0E0E6', line=dict(width=0)),
                showlegend=False,
                hoverinfo='skip'
            ),
            row=row, col=col
        )
        
        # Dark blue background (66-100)
        fig.add_trace(
            go.Bar(
                x=[label],
                y=[34],  # Height of this segment (100-66)
                base=66,
                orientation='v',
                marker=dict(color='#00008B', line=dict(width=0)),
                showlegend=False,
                hoverinfo='skip'
            ),
            row=row, col=col
        )
        
        # Add the actual value bar on top (green indicator)
        fig.add_trace(
            go.Bar(
                x=[label],
                y=[value],
                orientation='v',
                marker=dict(
                    color='#00E676',  # green indicator
                    line=dict(width=0)
                ),
                text=[f"{value:.1f}"],
                textposition='outside',
                textfont=dict(color='white', size=12),
                showlegend=False,
                hovertemplate=f'{label}: {value:.1f}<extra></extra>'
            ),
            row=row, col=col
        )
        
        # Update axes for each subplot
        fig.update_yaxes(
            range=[0, 100],
            showticklabels=True,
            tickmode='linear',
            tick0=0,
            dtick=50,
            row=row, col=col
        )
        fig.update_xaxes(showticklabels=False, row=row, col=col)

    fig.update_layout(
        height=700,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=50, b=20),
        title=dict(text="📊 Radial Civic Score Overview", font=dict(size=22)),
        barmode='overlay'
    )
    
    return fig
