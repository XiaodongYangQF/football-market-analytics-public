"""P8.1B unified public portfolio + genuine P7 forecast input UI.

Hosted forecasting fails closed. Owner Mac may connect original frozen worker
using scripts/run_owner_local.py, without bundling the scientific model.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from fma_portfolio.metrics import cumulative_by_source_date, group_summary, outcome_counts, summarize
from fma_portfolio.release import load_release
from fma_portfolio.prematch_receipts import read_receipts, ReceiptError, reconcile_public_settlement

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "public_v2.json"

st.set_page_config(
    page_title="Football Market Analytics | Research Portfolio",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""<style>
:root { --bg: #0b1120; }
.stApp { background: #0b1120; color: #e8eef8; }
[data-testid="stSidebar"] { background: #0e1829; border-right: 1px solid #1c2e47; }
.block-container { padding-top: 2.1rem; max-width: 1350px; }
.hero { background: linear-gradient(130deg,#122842 0%,#10283b 45%,#0e302c 100%);
    border:1px solid #2b4255; border-radius:20px; padding:30px 34px; margin-bottom: 24px; }
.eyebrow { color:#72d7d1; text-transform:uppercase; font-size:12px; font-weight:700;
    letter-spacing:.19em; margin-bottom:14px; }
.hero h1 { color:#f4f8ff; font-size:2.75rem; letter-spacing:-.04em;
    font-weight:750; margin:0 0 8px 0; }
.hero p { color:#b4c6d6; max-width:780px; font-size:1.03rem; line-height:1.65; margin:0; }
.note { border-left: 3px solid #4b92a8; background: #112136; color:#b6c9d9;
    padding: 15px 18px; border-radius:0 10px 10px 0; margin: 16px 0 26px 0; }
[data-testid="stMetric"] { padding: 20px 22px; border-radius:15px; border:1px solid #273b56;
    background: #111f32; }
[data-testid="stMetricLabel"] { color:#a6bad0; }
[data-testid="stMetricValue"] { color:#ecf4ff; }
hr { border-color:#23364e; }
</style>""", unsafe_allow_html=True)

release = load_release(DATA_PATH)
all_rows = release["records"]

with st.sidebar:
    st.markdown("### ⚽ FMA Research")
    st.caption("Public research · simulated performance")
    st.markdown("[Source code & public record history](https://github.com/XiaodongYangQF/football-market-analytics-public)")
    # Put auditable results first for public visitors. Real-time forecasts remain gated.
    page = st.radio(
        "Explore",
        ["Performance overview", "Pre-match archive", "Forecast ledger", "Methodology & limits", "Interactive forecast"],
        label_visibility="collapsed",
    )
    st.divider()
    if page != "Interactive forecast":
        markets = st.multiselect("Market", ["AH", "OU"], default=["AH", "OU"])
        leagues = sorted({r["competition"] for r in all_rows})
        selected_leagues = st.multiselect("Competition", leagues, default=leagues)
    else:
        markets = ["AH", "OU"]
        selected_leagues = sorted({r["competition"] for r in all_rows})
    st.divider()
    st.caption("PUBLIC V2 · fixed-policy snapshot")
    st.caption("Simulated results; not verified live trading returns.")

rows = [r for r in all_rows if r["market"] in markets and r["competition"] in selected_leagues]
metrics = summarize(rows)

if page != "Interactive forecast":
    st.markdown("""<section class="hero">
<div class="eyebrow">Independent quantitative research portfolio</div>
<h1>Football Market Analytics</h1>
<p>An auditable study of Asian Handicap and Asian Total market forecasts, recorded outcomes,
settlement consistency, and simulated economic performance.</p>
</section>""", unsafe_allow_html=True)

if page == "Interactive forecast":
    from fma_portfolio.p7.public_theme import apply_public_theme
    from fma_portfolio.p7.forecast_ui import forecast_page
    apply_public_theme()
    forecast_page()
    st.stop()

if page == "Pre-match archive":
    st.markdown("<div class='eyebrow'>Prospective research / server-timestamped forecast records</div>", unsafe_allow_html=True)
    st.subheader("Public pre-match forecast archive")
    st.caption("GitHub Issues contain the public forecast payload and server creation time; the repository holds a checked browsing copy.")
    st.warning("Kickoff times and input-quote provenance are user-declared, not independently certified. GitHub Issues can be edited or deleted. A late-published receipt is never classified as on time.")
    try:
        receipts = read_receipts(ROOT)
    except ReceiptError as exc:
        st.error(f"Receipt archive failed integrity validation: {exc}")
        st.stop()
    visible = []
    for item in receipts:
        for r in item["batch"]["records"]:
            visible.append({
                "GitHub published (UTC)": item["github_created_at_utc"],
                "Declared kickoff (UTC)": item["batch"]["kickoff_utc"],
                "Publication class": item["publication_class"],
                "League": r["competition"],
                "Fixture": f"{r['home_team']} vs {r['away_team']}",
                "AH": r["ah_direction"] if r["ah_status"] == "FORECAST" else "NO SIGNAL",
                "AH home line": r["ah_line"],
                "AH home odds": r["ah_home_odds"],
                "AH away odds": r["ah_away_odds"],
                "OU": r["ou_direction"] if r["ou_status"] == "FORECAST" else "NO SIGNAL",
                "OU line": r["asian_line"],
                "Over odds": r["asian_over_odds"],
                "Under odds": r["asian_under_odds"],
                "Over 2.5 odds": r["fixed_over_odds"],
                "Under 2.5 odds": r["fixed_under_odds"],
                "Model generated (local UTC)": r["saved_at_utc"],
                "Policy": r["policy_version"],
                "AH public settlement (strict match)": reconcile_public_settlement(r, "AH", all_rows),
                "OU public settlement (strict match)": reconcile_public_settlement(r, "OU", all_rows),
                "Batch SHA256": item["batch_sha256"],
                "GitHub Issue": item["github_issue_url"],
            })
    left, right, third = st.columns(3)
    left.metric("Published batches", len(receipts))
    right.metric("Recorded fixtures", len(visible))
    third.metric("Published before declared kickoff", sum(x["publication_class"] == "ON_TIME_DECLARED" for x in visible))
    if not visible:
        st.info("No prospective GitHub receipts have been published yet. Historical Local Public performance is separate and cannot be relabeled retrospectively.")
    else:
        leagues_for_receipts = sorted({x["League"] for x in visible})
        chosen = st.multiselect("League (public receipts)", leagues_for_receipts, default=leagues_for_receipts)
        shown = [x for x in visible if x["League"] in chosen]
        st.dataframe(pd.DataFrame(shown), use_container_width=True, hide_index=True, height=530,
                     column_config={"GitHub Issue": st.column_config.LinkColumn("Original public Issue", display_text="Open receipt")})
        st.download_button("Download selected public receipts (CSV)",
                           pd.DataFrame(shown).to_csv(index=False).encode("utf-8-sig"),
                           file_name="fma_prospective_receipts.csv", mime="text/csv")
        st.caption("Settlement links require an exact match in date, league, teams, direction, line and saved quote (for signals). Unmatched records remain unlinked; receipts never enter P&L a second time.")

elif page == "Performance overview":
    st.markdown("<div class='eyebrow'>Performance / public V2 cohort</div>", unsafe_allow_html=True)
    a, b, c, d = st.columns(4, gap="medium")
    a.metric("Settled signals", f"{metrics['settled_signals']}")
    b.metric("Weighted ROI", "—" if metrics["roi_pct"] is None else f"{metrics['roi_pct']:+.2f}%")
    c.metric("Simulated P&L", f"{metrics['pnl_u']:+.2f}u")
    d.metric("Fixture coverage", str(metrics["fixture_count"]))
    st.markdown("""<div class="note"><b>Research interpretation:</b> Returns are simulated using saved
    public quotes with 1u stake per settled signal. AH and OU on the same fixture are correlated;
    short-horizon ROI does not establish a persistent market edge. For OU, quotes are recorded as
    exploratory rather than confirmed executable prices.</div>""", unsafe_allow_html=True)
    left, right = st.columns([1.12, 1], gap="large")
    with left:
        st.subheader("Cumulative simulated P&L")
        timeline = pd.DataFrame(cumulative_by_source_date(rows))
        if timeline.empty or timeline["settled_signals"].sum() == 0:
            st.info("No settled signals in the selected filters.")
        else:
            fig = px.line(timeline, x="source_date", y="cumulative_pnl_u", markers=True,
                          labels={"source_date": "Stored fixture date", "cumulative_pnl_u": "P&L (u)"})
            fig.update_traces(line_color="#4fd6cb", line_width=3, marker_size=9)
            fig.update_layout(height=345, margin=dict(l=12, r=12, t=15, b=10),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#cbd9e7", showlegend=False,
                              xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#29405a", zerolinecolor="#8094a6"))
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Performance by market")
        market_data = pd.DataFrame(group_summary(rows, "market"))
        if market_data.empty or market_data["settled_signals"].sum() == 0:
            st.info("No settled market records in these filters.")
        else:
            fig = px.bar(market_data, x="market", y="pnl_u", text="pnl_u",
                         labels={"market": "Market", "pnl_u": "Net P&L (u)"},
                         color="market", color_discrete_map={"AH": "#6990cf", "OU": "#49cdb9"})
            fig.update_traces(texttemplate="%{text:+.3f}u", textposition="outside")
            fig.update_layout(height=345, margin=dict(l=12, r=12, t=15, b=10),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#cbd9e7", showlegend=False,
                              yaxis=dict(gridcolor="#29405a", zerolinecolor="#8094a6"))
            st.plotly_chart(fig, use_container_width=True)
    st.subheader("Market diagnostics")
    df = pd.DataFrame(group_summary(rows, "market"))
    if not df.empty:
        df = df.rename(columns={"market": "Market", "settled_signals": "Settled",
                                "fixture_count": "Fixtures", "turnover_u": "Turnover (u)",
                                "pnl_u": "P&L (u)", "roi_pct": "ROI (%)"})
        st.dataframe(df, use_container_width=True, hide_index=True)
    outcomes = outcome_counts(rows)
    st.caption("Outcome mix: " + (" · ".join(f"{key.replace('_', ' ').title()}: {val}" for key, val in outcomes.items()) if outcomes else "None"))

elif page == "Forecast ledger":
    st.subheader("Public V2 forecast ledger")
    st.caption("This view includes NO SIGNAL and unrecorded rows, but those rows do not contribute to P&L.")
    states = sorted({r["state"] for r in rows})
    selected = st.multiselect("Record state", states, default=states)
    display = []
    for r in rows:
        if r["state"] not in selected:
            continue
        direction = r["direction"]
        line = r["line"]
        line_label = "—" if line is None else f"{line:+g}" if r["market"] == "AH" else f"{line:g}"
        display.append({
            "Source date": r["source_date"], "Competition": r["competition"],
            "Fixture": r["fixture"], "Market": r["market"], "Forecast": direction,
            "Line": line_label, "Decimal odds": r["decimal_odds"],
            "Final score": r["final_score"], "State": r["state"],
            "Settlement": r["settlement"], "P&L (u)": r["pnl_u"],
            "Price evidence": r["price_evidence"],
        })
    frame = pd.DataFrame(display)
    if frame.empty:
        st.info("No records match the selected filters.")
    else:
        st.dataframe(frame, use_container_width=True, hide_index=True, height=590)
        st.download_button("Download filtered public ledger CSV",
                           data=frame.to_csv(index=False).encode("utf-8-sig"),
                           mime="text/csv", file_name="fma_public_v2_filtered.csv")
    st.info("Dates shown are the source snapshot's fixture-date fields. Some have not been independently normalized to official schedules.")

else:
    st.subheader("Research objective")
    st.write("Evaluate whether a deterministic, fixed-policy mapping from pre-match market inputs "
             "to AH/OU forecast directions can be reproduced and assessed against subsequent outcomes.")
    st.subheader("Methodological boundaries")
    st.markdown("""
- **Source inputs:** pre-match market observations; capture and replay can occur at separate times.
- **Public output:** previously recorded forecast directions and a transparent simulated settlement ledger.
- **Scoping:** this dataset contains *only* the post-activation Public V2 cohort, not the earlier strategy or retrospective replays.
- **Settlement:** 1u per recorded signal; Asian quarter-lines allow half-win and half-loss outcomes.
- **Quote provenance:** AH includes frozen execution quotes; OU includes exploratory main-line quotes, not a guarantee of tradability.
- **Validation status:** arithmetic has been checked against saved records, not independently certified by a bookmaker or exchange.
- **Statistical limits:** The initial snapshot contained 34 settled signals across 24 fixtures. Daily updates do not establish a persistent market edge. Multi-market signals within a match are not independent.
- **Public prematch receipts:** GitHub Issue publication and original quoted inputs are archived separately from historical performance. User-declared kickoff times and market quotes are not independently validated.
- **No live trading:** this public site never accesses a betting account or places bets. Hosted mode cannot call the private forecasting engine; the separate owner-local mode can use its frozen worker.
""")
    st.subheader("Evaluation priorities")
    st.write("Expand fixed-policy forward evaluation; compare against market-only baselines; "
             "track calibration when probabilistic outputs are available; report the outcome of no-signal cases; "
             "quantify uncertainty at the fixture level.")
    st.caption("Detailed design and caveats are in docs/methodology.md and docs/evaluation.md.")

st.divider()
st.caption(f"Release: curated public data only · Source snapshot {release['source_snapshot_generated_at_utc']} · No Private scientific or storage dependencies")
