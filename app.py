"""
Media Diet Diagnostic — Hackathon Edition
Analyzes the political bias, diversity, and blind spots in your internet following.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import logging

from config import APP_CONFIG, BIAS_COLORS, RELIABILITY_COLORS, get_anthropic_api_key
from src.utils import setup_logging, parse_sources_text, get_bias_label, get_bias_color
from src.social_scraper import enrich_sources
from src.bias_analyzer import classify_sources, analyze_diet, DEMO_CLASSIFIED, DEMO_DIET

setup_logging()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=APP_CONFIG["page_title"],
    page_icon=APP_CONFIG["page_icon"],
    layout=APP_CONFIG["layout"],
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
.hero-title { font-size: 3rem; font-weight: 800; line-height: 1.1; }
.hero-sub { font-size: 1.2rem; color: #888; margin-bottom: 1.5rem; }
.metric-card {
    background: #1e1e2e; border-radius: 12px; padding: 1.2rem 1.5rem;
    text-align: center; border: 1px solid #2a2a3e;
}
.metric-card .label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
.metric-card .value { font-size: 2rem; font-weight: 700; margin: 0.3rem 0; }
.metric-card .sub { font-size: 0.85rem; color: #aaa; }
.source-tag {
    display: inline-block; border-radius: 20px; padding: 2px 10px;
    font-size: 0.75rem; font-weight: 600; margin: 2px;
}
.section-header {
    font-size: 1.4rem; font-weight: 700; margin: 2rem 0 0.5rem;
    border-bottom: 1px solid #2a2a3e; padding-bottom: 0.5rem;
}
.blind-spot-item { padding: 0.5rem 0; border-bottom: 1px solid #1e1e2e; }
.recommendation-card {
    background: #1e1e2e; border-radius: 8px; padding: 0.8rem 1rem;
    margin-bottom: 0.5rem; border-left: 3px solid #7c4dff;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Visualization helpers
# ---------------------------------------------------------------------------

def spectrum_chart(score: float, distribution: dict) -> go.Figure:
    """Political spectrum gauge with user position indicator."""
    sections = [
        (-10, -6, BIAS_COLORS["Far Left"], "Far Left"),
        (-6, -3, BIAS_COLORS["Left"], "Left"),
        (-3, -1, BIAS_COLORS["Center-Left"], "Center-Left"),
        (-1, 1, BIAS_COLORS["Center"], "Center"),
        (1, 3, BIAS_COLORS["Center-Right"], "Center-Right"),
        (3, 6, BIAS_COLORS["Right"], "Right"),
        (6, 10, BIAS_COLORS["Far Right"], "Far Right"),
    ]

    fig = go.Figure()

    for x0, x1, color, label in sections:
        count = distribution.get(label, 0)
        fig.add_shape(
            type="rect", x0=x0, x1=x1, y0=0, y1=1,
            fillcolor=color, opacity=0.75, line_width=0,
        )
        fig.add_annotation(
            x=(x0 + x1) / 2, y=0.5, text=f"<b>{label}</b><br>{count}",
            showarrow=False, font=dict(color="white", size=10),
        )

    # User position indicator
    fig.add_trace(go.Scatter(
        x=[score], y=[1.15],
        mode="markers+text",
        marker=dict(symbol="triangle-down", size=22, color="#facc15",
                    line=dict(color="#000", width=1.5)),
        text=[f"You: {score:+.1f}"],
        textposition="top center",
        textfont=dict(size=12, color="#facc15"),
        hovertemplate=f"Your aggregate bias score: {score:+.1f}<extra></extra>",
        name="Your position",
    ))

    fig.update_layout(
        showlegend=False,
        height=160,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(range=[-11, 11], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[-0.1, 1.5], showgrid=False, zeroline=False, showticklabels=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def content_donut(content_distribution: dict) -> go.Figure:
    labels = list(content_distribution.keys())
    values = list(content_distribution.values())
    colors = px.colors.qualitative.Bold[: len(labels)]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#0e0e1a", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11),
        hovertemplate="%{label}: %{value} sources<extra></extra>",
    ))
    fig.update_layout(
        showlegend=False, height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def reliability_bar(reliability_distribution: dict) -> go.Figure:
    order = ["high", "medium", "low", "unknown"]
    labels = [k.capitalize() for k in order]
    values = [reliability_distribution.get(k, 0) for k in order]
    colors = [RELIABILITY_COLORS[k] for k in order]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=values, textposition="outside",
        hovertemplate="%{x}: %{y} sources<extra></extra>",
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=False, zeroline=False),
        xaxis=dict(showgrid=False),
        showlegend=False,
    )
    return fig


def echo_chamber_gauge(score: int) -> go.Figure:
    color = "#4caf50" if score < 40 else "#ff9800" if score < 70 else "#f44336"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"size": 28}},
        gauge={
            "axis": {"range": [0, 100], "showticklabels": True, "tickfont": {"size": 10}},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "#1e1e2e",
            "steps": [
                {"range": [0, 40], "color": "#1b3a1f"},
                {"range": [40, 70], "color": "#3a2e1b"},
                {"range": [70, 100], "color": "#3a1b1b"},
            ],
            "threshold": {"line": {"color": color, "width": 3}, "thickness": 0.8, "value": score},
        },
    ))
    fig.update_layout(
        height=200, margin=dict(l=20, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"),
    )
    return fig


# ---------------------------------------------------------------------------
# Source table
# ---------------------------------------------------------------------------

def render_source_table(classified_sources: list[dict]):
    rows = []
    for s in classified_sources:
        a = s.get("analysis", {})
        label = a.get("political_label", "Unknown")
        color = BIAS_COLORS.get(label, "#78909c")
        reliability = a.get("reliability", "unknown")
        rel_color = RELIABILITY_COLORS.get(reliability, "#9e9e9e")
        rows.append({
            "Source": a.get("source", s["name"]),
            "Platform": s.get("platform", "?").capitalize(),
            "Leaning": label,
            "Bias Score": f"{a.get('political_leaning_score', 0):+.1f}",
            "Reliability": reliability.capitalize(),
            "Known for": a.get("known_for", ""),
            "Categories": ", ".join(a.get("content_categories", [])),
        })

    df = pd.DataFrame(rows)

    def color_leaning(val):
        c = BIAS_COLORS.get(val, "#78909c")
        return f"color: {c}; font-weight: 600"

    def color_reliability(val):
        c = RELIABILITY_COLORS.get(val.lower(), "#9e9e9e")
        return f"color: {c}; font-weight: 600"

    styled = df.style.applymap(color_leaning, subset=["Leaning"]) \
                     .applymap(color_reliability, subset=["Reliability"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Results dashboard
# ---------------------------------------------------------------------------

def render_results(classified_sources: list[dict], diet: dict):
    score = diet.get("overall_bias_score", 0)
    label = diet.get("overall_bias_label", "Unknown")
    echo = diet.get("echo_chamber_score", 50)
    grade = diet.get("diversity_grade", "?")

    st.markdown("---")
    st.markdown(
        f'<div class="hero-title">Your Media Diet Report</div>'
        f'<p class="hero-sub">{len(classified_sources)} sources analyzed</p>',
        unsafe_allow_html=True,
    )

    # Top metric cards
    col1, col2, col3, col4 = st.columns(4)
    bias_color = get_bias_color(score)
    echo_color = "#4caf50" if echo < 40 else "#ff9800" if echo < 70 else "#f44336"
    grade_color = {"A": "#4caf50", "B": "#8bc34a", "C": "#ff9800", "D": "#ff5722", "F": "#f44336"}.get(grade, "#888")

    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="label">Overall Lean</div>'
            f'<div class="value" style="color:{bias_color};">{score:+.1f}</div>'
            f'<div class="sub">{label}</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="metric-card"><div class="label">Diversity Grade</div>'
            f'<div class="value" style="color:{grade_color};">{grade}</div>'
            f'<div class="sub">Content variety</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="metric-card"><div class="label">Echo Chamber</div>'
            f'<div class="value" style="color:{echo_color};">{echo}%</div>'
            f'<div class="sub">{"Low risk" if echo < 40 else "Moderate" if echo < 70 else "High risk"}</div></div>',
            unsafe_allow_html=True,
        )
    with col4:
        rel = diet.get("reliability_distribution", {})
        high_pct = round(rel.get("high", 0) / max(sum(rel.values()), 1) * 100)
        st.markdown(
            f'<div class="metric-card"><div class="label">High-Reliability</div>'
            f'<div class="value" style="color:#4caf50;">{high_pct}%</div>'
            f'<div class="sub">of your sources</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Political spectrum
    st.markdown('<div class="section-header">Political Spectrum</div>', unsafe_allow_html=True)
    pol_dist = diet.get("political_distribution", {})
    st.plotly_chart(spectrum_chart(score, pol_dist), use_container_width=True)
    st.caption(f"Score range: -10 (Far Left) → +10 (Far Right). Your aggregate: **{score:+.1f}** ({label})")

    # Summary
    st.info(diet.get("summary", ""))

    # Charts row
    st.markdown('<div class="section-header">Content Breakdown &amp; Source Reliability</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Content Categories**")
        cd = diet.get("content_distribution", {})
        if cd:
            st.plotly_chart(content_donut(cd), use_container_width=True)
    with c2:
        st.markdown("**Source Reliability**")
        rd = diet.get("reliability_distribution", {})
        if rd:
            st.plotly_chart(reliability_bar(rd), use_container_width=True)

    # Echo chamber + dominant topics
    st.markdown('<div class="section-header">Echo Chamber &amp; Topics</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("**Echo Chamber Risk**")
        st.plotly_chart(echo_chamber_gauge(echo), use_container_width=True)
    with c2:
        st.markdown("**Dominant Topics You're Exposed To**")
        for topic in diet.get("dominant_topics", []):
            st.markdown(f"- {topic}")
        st.markdown("**What Your Feed Over-Indexes On**")
        for item in diet.get("what_you_see_more_of", []):
            st.markdown(f"- {item}")

    # Key insights
    st.markdown('<div class="section-header">Key Insights</div>', unsafe_allow_html=True)
    for insight in diet.get("key_insights", []):
        st.markdown(f"> {insight}")

    # Blind spots
    st.markdown('<div class="section-header">Your Media Blind Spots</div>', unsafe_allow_html=True)
    st.caption("Perspectives and topics that are missing or underrepresented in your current feed.")
    for spot in diet.get("blind_spots", []):
        st.markdown(f"- {spot}")

    # Recommendations
    st.markdown('<div class="section-header">Recommendations to Balance Your Diet</div>', unsafe_allow_html=True)
    recs = diet.get("recommendations", [])
    if recs:
        for r in recs:
            if isinstance(r, dict):
                st.markdown(
                    f'<div class="recommendation-card"><strong>{r.get("source","")}</strong> — {r.get("reason","")}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"- {r}")

    # Source-by-source breakdown
    st.markdown('<div class="section-header">Source-by-Source Breakdown</div>', unsafe_allow_html=True)
    render_source_table(classified_sources)


# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------

DEMO_INPUT = """@CNN
@FoxNews
@NYTimes
@TheGuardian
@elonmusk
r/worldnews
r/technology
r/Conservative
r/nba
Veritasium"""

PLACEHOLDER = """Examples:
@CNN
@FoxNews
r/worldnews
r/technology
youtube.com/@veritasium
theguardian.com
@elonmusk"""

st.markdown(
    '<div class="hero-title">🔬 Media Diet Diagnostic</div>'
    '<p class="hero-sub">Find out what your internet following says about your media diet — '
    'political lean, diversity, echo chamber risk, and blind spots.</p>',
    unsafe_allow_html=True,
)
st.markdown("Inspired by **Ground News** — built for your whole internet, not just news articles.")
st.markdown("---")

has_api_key = bool(get_anthropic_api_key())
if not has_api_key:
    st.warning(
        "No **ANTHROPIC_API_KEY** found. You can still try the demo below, "
        "but live analysis requires an API key set in your `.env` file.",
        icon="⚠️",
    )

col_input, col_tips = st.columns([3, 2])

with col_input:
    st.markdown("### Paste your follows")
    st.caption("One per line — @Twitter handles, r/subreddits, YouTube channels, or website URLs.")
    user_input = st.text_area(
        "Your follows",
        placeholder=PLACEHOLDER,
        height=240,
        label_visibility="collapsed",
    )

with col_tips:
    st.markdown("### Supported formats")
    st.markdown("""
| Format | Example |
|--------|---------|
| Twitter/X handle | `@CNN` |
| Subreddit | `r/worldnews` |
| YouTube channel | `youtube.com/@veritasium` |
| News website | `bbc.com` |
| Any name | `Fox News` |

**Tips:**
- Add 10–50 sources for the best analysis
- Mix news, entertainment, and politics
- Include sources across the spectrum for fair results
    """)

col_run, col_demo = st.columns([1, 1])
with col_run:
    run_btn = st.button(
        "Run Diagnostic",
        type="primary",
        use_container_width=True,
        disabled=not has_api_key and not user_input,
    )
with col_demo:
    demo_btn = st.button("Try Demo (no API key needed)", use_container_width=True)

# ---------------------------------------------------------------------------
# Analysis & results
# ---------------------------------------------------------------------------

if demo_btn:
    st.success("Loading demo results...")
    render_results(DEMO_CLASSIFIED, DEMO_DIET)

elif run_btn:
    if not user_input.strip():
        st.error("Please paste at least one source in the input box above.")
    elif not has_api_key:
        st.error("Set ANTHROPIC_API_KEY in your .env file to run a live analysis.")
    else:
        sources = parse_sources_text(user_input)
        if not sources:
            st.error("Could not parse any sources. Check the format and try again.")
        else:
            st.info(f"Found **{len(sources)} sources** to analyze. Starting diagnostic...")

            with st.spinner("Fetching metadata for Reddit sources..."):
                enriched = enrich_sources(sources)

            progress = st.progress(0, text="Classifying sources with Claude...")
            with st.spinner("Analyzing each source for bias, category, and reliability..."):
                classified = classify_sources(enriched)
            progress.progress(60, text="Running overall diet analysis...")

            with st.spinner("Generating your media diet report..."):
                diet = analyze_diet(classified)
            progress.progress(100, text="Done!")
            progress.empty()

            st.success(f"Analysis complete for {len(classified)} sources!")
            render_results(classified, diet)
else:
    # Welcome / how it works
    st.markdown("---")
    st.markdown("### How it works")
    cols = st.columns(3)
    with cols[0]:
        st.markdown("**1. Paste your follows**")
        st.markdown("Add the accounts, subreddits, YouTube channels, and news sites you follow — one per line.")
    with cols[1]:
        st.markdown("**2. AI analyses each source**")
        st.markdown("Claude reads the sources and classifies political leaning, content category, and reliability.")
    with cols[2]:
        st.markdown("**3. Get your diagnostic**")
        st.markdown("See your overall bias score, echo chamber risk, blind spots, and personalised recommendations.")

    st.markdown("---")
    st.caption("Media Diet Diagnostic — Hackathon Project. Analysis powered by Claude (Anthropic).")
