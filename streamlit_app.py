from decimal import Decimal
from pathlib import Path
import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from plotly.subplots import make_subplots

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from dashboard.data_access import load_gold_data  # noqa: E402

st.set_page_config(
    page_title="NYC Taxi | Analytics",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ───────────────────────── Design tokens ─────────────────────────
BG = "#F4F6FA"
SIDEBAR = "#FFFFFF"
CARD = "#FFFFFF"
CARD_HI = "#FAFBFD"
BORDER = "#E3E8F0"
TEXT = "#0F172A"
SUBTLE = "#334155"
MUTED = "#64748B"
YELLOW = "#F5B400"   # primary (NYC taxi yellow)
TEAL = "#0D9488"
VIOLET = "#7C3AED"
CORAL = "#E11D48"
GREEN = "#059669"

SEQ_YELLOW = ["#FFF6DB", "#FFC72C", "#B45309"]
SEQ_TEAL = ["#D9F5F1", "#2DD4BF", "#0F766E"]
PALETTE = [YELLOW, TEAL, VIOLET, CORAL, "#60A5FA", "#F59E0B"]

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background: {BG}; color: {TEXT}; }}
    [data-testid="stHeader"] {{ background: transparent; }}
    #MainMenu, footer {{ visibility: hidden; }}

    .block-container {{ max-width: 1500px; padding: 1.4rem 2.2rem 1.5rem; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{ background: {SIDEBAR}; border-right: 1px solid {BORDER}; }}
    [data-testid="stSidebar"] * {{ color: {SUBTLE}; }}
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {{ gap: 4px; }}
    [data-testid="stSidebar"] [data-testid="stRadio"] label {{
        padding: 10px 12px; border-radius: 10px; font-size: 14px; font-weight: 500;
        border: 1px solid transparent; transition: all .15s ease; width: 100%;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{ background: {CARD}; }}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
        background: rgba(245,180,0,.16);
        border-color: rgba(245,180,0,.55); color: {TEXT};
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) * {{ color: {TEXT}; font-weight: 700; }}
    [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {{ display: none; }}

    .brand {{ font-size: 24px; font-weight: 900; letter-spacing: -.8px; color: {TEXT}; }}
    .brand span {{ color: {YELLOW}; }}
    .brand-sub {{ color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 2.2px; margin: 2px 0 14px; }}
    .side-label {{ color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 1.8px; margin: 14px 0 8px; }}
    .side-pill {{
        display:flex; justify-content:space-between; font-size:12px; padding:8px 10px;
        background:{CARD}; border:1px solid {BORDER}; border-radius:8px; margin-bottom:6px;
    }}
    .side-pill b {{ color:{TEXT}; font-weight:600; }}

    /* Hero header */
    .hero {{
        position: relative; overflow: hidden;
        background: linear-gradient(120deg, #FFFFFF 0%, #FFF8E1 100%); box-shadow: 0 4px 14px rgba(15,23,42,.05);
        border: 1px solid {BORDER}; border-radius: 18px; padding: 22px 28px; margin-bottom: 18px;
    }}
    .hero:after {{
        content: "🚕"; position: absolute; right: 26px; top: 6px; font-size: 92px; opacity: .14;
    }}
    .hero-eyebrow {{ color: #B45309; font-size: 11px; font-weight: 800; letter-spacing: 2.2px; }}
    .hero-title {{ color: {TEXT}; font-size: 34px; font-weight: 900; letter-spacing: -1.2px; line-height: 1.15; margin: 4px 0; }}
    .hero-sub {{ color: {MUTED}; font-size: 13px; }}

    /* KPI */
    .kpi {{
        background: linear-gradient(160deg, {CARD_HI}, {CARD}); border: 1px solid {BORDER};
        border-radius: 16px; padding: 18px 20px 16px; height: 100%; min-height: 138px; box-shadow: 0 2px 8px rgba(15,23,42,.05);
        position: relative; overflow: hidden;
    }}
    .kpi:before {{
        content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--accent, {YELLOW});
    }}
    .kpi-top {{ display:flex; justify-content:space-between; align-items:center; }}
    .kpi-label {{ color: {MUTED}; font-size: 12px; font-weight: 700; letter-spacing: .8px; text-transform: uppercase; }}
    .kpi-icon {{
        width: 34px; height: 34px; border-radius: 10px; display:flex; align-items:center; justify-content:center;
        font-size: 17px; background: #F1F5F9;
    }}
    .kpi-value {{
        color: {TEXT}; font-size: 40px; font-weight: 900; letter-spacing: -1.6px; line-height: 1.1; margin: 12px 0 6px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    .kpi-value.small {{ font-size: 28px; letter-spacing: -.8px; }}
    .kpi-foot {{ display:flex; align-items:center; gap:8px; color:{MUTED}; font-size:12px; }}
    .chip {{ padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 800; }}
    .chip.up {{ background: rgba(52,211,153,.14); color: {GREEN}; }}
    .chip.down {{ background: rgba(251,113,133,.14); color: {CORAL}; }}

    /* Sections */
    .section-heading {{ color:{TEXT}; font-size:18px; font-weight:800; letter-spacing:-.3px; margin: 4px 0 0; }}
    .section-caption {{ color:{MUTED}; font-size:12px; margin-bottom: 8px; }}

    /* Insight strip */
    .insight {{
        background: rgba(255,199,44,.06); border: 1px solid rgba(255,199,44,.25); border-radius: 12px;
        padding: 12px 16px; color: {SUBTLE}; font-size: 13.5px; line-height: 1.5; height: 100%;
    }}
    .insight b {{ color: #B45309; }}

    .badge {{ display:inline-block; padding:5px 12px; border-radius:999px; font-size:12px; font-weight:800; }}
    .badge.ok {{ background: rgba(52,211,153,.14); color:{GREEN}; }}
    .badge.warn {{ background: rgba(245,180,0,.18); color:#B45309; }}
    .badge.bad {{ background: rgba(251,113,133,.14); color:{CORAL}; }}

    /* Streamlit widgets on dark */
    div[data-testid="stPlotlyChart"] {{
        background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; padding: 8px 10px 2px; box-shadow: 0 2px 8px rgba(15,23,42,.05);
    }}
    div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 12px; overflow: hidden; }}
    div[data-testid="stExpander"] {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
    div[data-testid="stAlert"] {{ border-radius: 12px; }}
    .stButton > button {{
        background: {YELLOW}; color: #111827; font-weight: 800; border: 0; border-radius: 10px;
    }}
    .stButton > button:hover {{ background: #FFD65C; color: #111827; }}
    .stButton > button, .stButton > button * {{ color: #111827 !important; }}

    .footer {{ color:{MUTED}; font-size:11px; border-top:1px solid {BORDER}; padding-top:12px; margin-top:22px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ───────────────────────── Helpers ─────────────────────────
def esc(v):
    return html.escape(str(v))


def compact(v, prefix="", decimals=2):
    """1,234,567 -> 1.23M  |  fixes the 'unreadable numbers' problem."""
    if v is None or pd.isna(v):
        return "—"
    a = abs(v)
    if a >= 1e9:
        return f"{prefix}{v / 1e9:.{decimals}f}B"
    if a >= 1e6:
        return f"{prefix}{v / 1e6:.{decimals}f}M"
    if a >= 1e3:
        return f"{prefix}{v / 1e3:.1f}K"
    return f"{prefix}{v:,.0f}"


def money(v, decimals=2):
    return f"${v:,.{decimals}f}" if pd.notna(v) else "—"


def has(df, *cols):
    return not df.empty and all(c in df.columns for c in cols)


def page_header(eyebrow, title, subtitle):
    st.markdown(
        f"""<div class="hero">
            <div class="hero-eyebrow">{esc(eyebrow)}</div>
            <div class="hero-title">{esc(title)}</div>
            <div class="hero-sub">{esc(subtitle)}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def section_title(title, subtitle=""):
    st.markdown(
        f"""<div class="section-heading">{esc(title)}</div>
        <div class="section-caption">{esc(subtitle)}</div>""",
        unsafe_allow_html=True,
    )


def kpi_card(label, value, icon, note="", delta=None, accent=YELLOW, small=False):
    chip = ""
    if delta is not None and pd.notna(delta):
        cls = "up" if delta >= 0 else "down"
        arrow = "▲" if delta >= 0 else "▼"
        chip = f'<span class="chip {cls}">{arrow} {abs(delta):.1f}%</span>'
    size = "kpi-value small" if small else "kpi-value"
    st.markdown(
        f"""<div class="kpi" style="--accent:{accent}">
            <div class="kpi-top">
                <span class="kpi-label">{esc(label)}</span>
                <span class="kpi-icon">{esc(icon)}</span>
            </div>
            <div class="{size}">{esc(value)}</div>
            <div class="kpi-foot">{chip}<span>{esc(note)}</span></div>
        </div>""",
        unsafe_allow_html=True,
    )


def insight(text):
    st.markdown(f'<div class="insight">💡 {text}</div>', unsafe_allow_html=True)


def chart_style(fig, height=340):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=10, t=24, b=10),
        font=dict(family="Inter, sans-serif", color=SUBTLE, size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
        hoverlabel=dict(bgcolor="#0F172A", bordercolor=YELLOW, font=dict(color="white", size=13)),
        coloraxis_showscale=False,
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDER, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor="#EEF2F7", zeroline=False, tickfont=dict(color=MUTED))
    return fig


def show_chart(fig, key, height=340):
    # theme=None -> stop Streamlit from overriding our fonts/colors (this made legends invisible)
    st.plotly_chart(chart_style(fig, height), use_container_width=True, key=key, theme=None,
                    config={"displayModeBar": False})


def share_bars(df, label_col, value_col, key, height=340, value_prefix="", color=YELLOW, min_pct=0.0):
    """Clear replacement for crowded donuts: ranked bars labelled 'xx.x% · value'."""
    d = (df.groupby(label_col, as_index=False, dropna=False)[value_col].sum()
         .sort_values(value_col, ascending=False))
    d[label_col] = d[label_col].fillna("Unknown").astype(str)
    total = d[value_col].sum()
    d["pct"] = d[value_col] / total * 100 if total else 0
    if min_pct:
        small = d["pct"] < min_pct
        if small.sum() > 1:
            other = d[small][[value_col]].sum()
            d = pd.concat([d[~small],
                           pd.DataFrame({label_col: ["Other"], value_col: [other[value_col]],
                                         "pct": [other[value_col] / total * 100]})], ignore_index=True)
    d = d.sort_values("pct", ascending=True)
    labels = [f"<b>{p:.1f}%</b>  ·  {compact(v, value_prefix)}" for p, v in zip(d["pct"], d[value_col])]
    fig = go.Figure(go.Bar(
        x=d["pct"], y=d[label_col], orientation="h", marker_color=color,
        text=labels, textposition="outside", textfont=dict(color=TEXT, size=13), cliponaxis=False,
        hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>"))
    fig.update_xaxes(visible=False, range=[0, max(d["pct"].max() * 1.45, 1)])
    fig.update_yaxes(tickfont=dict(color=TEXT, size=13), showgrid=False)
    fig.update_layout(showlegend=False)
    show_chart(fig, key, height)


def get_data(table_name):
    try:
        df = load_gold_data(table_name).copy()
        # Snowflake returns NUMBER columns as decimal.Decimal -> convert to float
        for col in df.columns:
            if df[col].dtype == object and df[col].map(lambda x: isinstance(x, Decimal)).any():
                df[col] = pd.to_numeric(
                    df[col].map(lambda x: float(x) if isinstance(x, Decimal) else x),
                    errors="coerce",
                )
        return df
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load {table_name} from Snowflake.")
        with st.expander("Technical details"):
            st.exception(exc)
        return pd.DataFrame()


# ───────────────────────── Sidebar ─────────────────────────
with st.sidebar:
    st.markdown('<div class="brand">🚕 NYC <span>Taxi</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">ANALYTICS PLATFORM</div>', unsafe_allow_html=True)

    st.markdown('<div class="side-label">WORKSPACE</div>', unsafe_allow_html=True)
    pages = [
        "📊  Executive Overview",
        "⏱️  Demand Analytics",
        "🗺️  Zone & Route Intelligence",
        "💳  Revenue & Payments",
        "🛡️  Data Quality & Health",
    ]
    page = st.radio("Navigation", pages, label_visibility="collapsed")

    st.markdown('<div class="side-label">DATA PLATFORM</div>', unsafe_allow_html=True)
    st.markdown('<div class="side-pill"><span>Warehouse</span><b>Snowflake</b></div>', unsafe_allow_html=True)
    st.markdown('<div class="side-pill"><span>Layer</span><b>GOLD</b></div>', unsafe_allow_html=True)
    st.markdown('<div class="side-pill"><span>Cache</span><b>5 min</b></div>', unsafe_allow_html=True)
    st.write("")
    if st.button("↻  Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ───────────────────────── 1. Executive Overview ─────────────────────────
if page.endswith("Executive Overview"):
    page_header("BUSINESS INTELLIGENCE", "Executive Overview",
                "Trip volume, revenue and performance at a glance.")

    daily = get_data("DAILY_TRIPS")
    monthly = get_data("MONTHLY_SUMMARY")

    if has(daily, "pickup_date", "total_trips", "total_revenue"):
        daily["pickup_date"] = pd.to_datetime(daily["pickup_date"], errors="coerce")
        daily = daily.dropna(subset=["pickup_date"]).sort_values("pickup_date")

        min_d, max_d = daily["pickup_date"].min().date(), daily["pickup_date"].max().date()
        picked = st.date_input("Reporting period", value=(min_d, max_d),
                               min_value=min_d, max_value=max_d, key="ov_range")
        filtered = daily
        if isinstance(picked, (tuple, list)) and len(picked) == 2:
            filtered = daily[daily["pickup_date"].dt.date.between(*picked)]
        if filtered.empty:
            st.warning("No data for this reporting period.")
            st.stop()

        trips = filtered["total_trips"].sum()
        revenue = filtered["total_revenue"].sum()
        avg_fare = (filtered["avg_fare"].mean() if "avg_fare" in filtered.columns
                    else revenue / trips if trips else float("nan"))
        dist = filtered["avg_distance_miles"].mean() if "avg_distance_miles" in filtered.columns else float("nan")

        mom = None
        if has(monthly, "revenue_mom_pct"):
            s = pd.to_numeric(monthly["revenue_mom_pct"], errors="coerce").dropna()
            mom = s.iloc[-1] if not s.empty else None

        c = st.columns(4, gap="medium")
        with c[0]:
            kpi_card("Total Trips", compact(trips), "🚕", f"{trips:,.0f} trips", accent=YELLOW)
        with c[1]:
            kpi_card("Total Revenue", compact(revenue, "$"), "💵", "Latest month MoM", delta=mom, accent=TEAL)
        with c[2]:
            kpi_card("Average Fare", money(avg_fare), "🏷️", "Per trip", accent=VIOLET)
        with c[3]:
            kpi_card("Avg. Distance", f"{dist:,.2f} mi" if pd.notna(dist) else "—", "📍", "Per trip", accent=CORAL)

        st.write("")
        best = filtered.loc[filtered["total_trips"].idxmax()]
        i = st.columns(3, gap="medium")
        with i[0]:
            insight(f"Busiest day was <b>{best['pickup_date']:%b %d, %Y}</b> with <b>{compact(best['total_trips'])}</b> trips.")
        with i[1]:
            insight(f"Average of <b>{compact(filtered['total_trips'].mean())}</b> trips and "
                    f"<b>{compact(filtered['total_revenue'].mean(), '$')}</b> revenue per day.")
        with i[2]:
            insight(f"The period covers <b>{len(filtered)}</b> days of activity.")

        st.write("")
        left, right = st.columns(2, gap="medium")
        with left:
            section_title("Trip Volume", "Daily trips with 7-day moving average")
            f = filtered.assign(ma7=filtered["total_trips"].rolling(7, min_periods=1).mean())
            fig = go.Figure()
            fig.add_bar(x=f["pickup_date"], y=f["total_trips"], name="Daily trips",
                        marker_color="rgba(245,180,0,.40)")
            fig.add_scatter(x=f["pickup_date"], y=f["ma7"], name="7-day avg",
                            line=dict(color=YELLOW, width=3))
            show_chart(fig, "ov_trips")
        with right:
            section_title("Revenue", "Daily revenue ($)")
            fig = px.area(filtered, x="pickup_date", y="total_revenue",
                          color_discrete_sequence=[TEAL],
                          labels={"pickup_date": "", "total_revenue": "Revenue ($)"})
            fig.update_traces(line=dict(width=3), fillcolor="rgba(13,148,136,.15)")
            show_chart(fig, "ov_rev")

        if has(monthly, "pickup_month", "total_revenue"):
            monthly["pickup_month"] = pd.to_datetime(monthly["pickup_month"], errors="coerce")
            monthly = monthly.dropna(subset=["pickup_month"]).sort_values("pickup_month")
            st.write("")
            section_title("Monthly Performance", "Revenue (bars) vs. trips (line)")
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=monthly["pickup_month"], y=monthly["total_revenue"], name="Revenue ($)",
                        marker_color=YELLOW,
                        text=[compact(v, "$") for v in monthly["total_revenue"]],
                        textposition="outside", textfont=dict(color=TEXT, size=12))
            if "total_trips" in monthly.columns:
                fig.add_scatter(x=monthly["pickup_month"], y=monthly["total_trips"], name="Trips",
                                mode="lines+markers", line=dict(color=TEAL, width=3),
                                marker=dict(size=9), secondary_y=True)
            fig.update_yaxes(secondary_y=True, showgrid=False)
            show_chart(fig, "ov_monthly", 380)

        with st.expander("Explore daily records"):
            st.dataframe(filtered, use_container_width=True, hide_index=True)
    else:
        st.info("DAILY_TRIPS is empty or is missing expected columns.")


# ───────────────────────── 2. Demand Analytics ─────────────────────────
elif page.endswith("Demand Analytics"):
    page_header("DEMAND INTELLIGENCE", "Demand Analytics",
                "When demand happens and how it moves through the week.")

    hourly = get_data("HOURLY_DEMAND")

    if has(hourly, "pickup_hour", "total_trips", "day_name", "day_of_week"):
        by_hour = hourly.groupby("pickup_hour", as_index=False)["total_trips"].sum().sort_values("pickup_hour")
        by_day = (hourly.groupby(["day_of_week", "day_name"], as_index=False)["total_trips"]
                  .sum().sort_values("day_of_week"))
        total = by_hour["total_trips"].sum()
        peak_h = int(by_hour.loc[by_hour["total_trips"].idxmax(), "pickup_hour"])
        peak_share = by_hour["total_trips"].max() / total * 100
        peak_d = by_day.loc[by_day["total_trips"].idxmax(), "day_name"]
        quiet_h = int(by_hour.loc[by_hour["total_trips"].idxmin(), "pickup_hour"])

        c = st.columns(4, gap="medium")
        with c[0]:
            kpi_card("Total Trips", compact(total), "🚕", "All hours & weekdays", accent=YELLOW)
        with c[1]:
            kpi_card("Peak Hour", f"{peak_h:02d}:00", "⚡", f"{peak_share:.1f}% of all trips", accent=TEAL)
        with c[2]:
            kpi_card("Busiest Weekday", peak_d, "📅", "By total trips", accent=VIOLET, small=True)
        with c[3]:
            kpi_card("Quietest Hour", f"{quiet_h:02d}:00", "🌙", "Lowest demand", accent=CORAL)

        st.write("")
        insight(f"Demand peaks at <b>{peak_h:02d}:00</b> and <b>{peak_d}</b> is the busiest day — "
                f"plan driver supply around these windows.")

        st.write("")
        section_title("Demand by Hour", "Highlighted bar = peak hour")
        colors = [YELLOW if h == peak_h else "#CBD5E1" for h in by_hour["pickup_hour"]]
        fig = go.Figure(go.Bar(x=by_hour["pickup_hour"], y=by_hour["total_trips"], marker_color=colors,
                               hovertemplate="%{x}:00 — %{y:,.0f} trips<extra></extra>"))
        fig.update_xaxes(dtick=1, title="Hour of day")
        show_chart(fig, "dm_hour")

        left, right = st.columns([1, 1.4], gap="medium")
        with left:
            section_title("Demand by Weekday", "Total trips")
            top_idx = by_day["total_trips"].idxmax()
            colors = [YELLOW if i == top_idx else "#CBD5E1" for i in by_day.index]
            fig = go.Figure(go.Bar(x=by_day["day_name"], y=by_day["total_trips"], marker_color=colors,
                                   text=[compact(v) for v in by_day["total_trips"]],
                                   textposition="outside", textfont=dict(color=TEXT)))
            show_chart(fig, "dm_day", 380)
        with right:
            section_title("Weekday × Hour Heatmap", "Darker = fewer trips, yellow = peak demand")
            order = by_day["day_name"].tolist()
            heat = (hourly.pivot_table(index="day_name", columns="pickup_hour",
                                       values="total_trips", aggfunc="sum").reindex(order))
            fig = px.imshow(heat, aspect="auto", color_continuous_scale=SEQ_YELLOW,
                            labels={"x": "Hour", "y": "", "color": "Trips"})
            fig.update_xaxes(dtick=1)
            show_chart(fig, "dm_heat", 380)

        with st.expander("Explore hourly demand records"):
            st.dataframe(hourly, use_container_width=True, hide_index=True)
    else:
        st.info("No hourly demand data is available.")


# ───────────────────────── 3. Zone & Route ─────────────────────────
elif page.endswith("Zone & Route Intelligence"):
    page_header("GEOSPATIAL PERFORMANCE", "Zone & Route Intelligence",
                "Top pickup zones, boroughs and the most popular routes.")

    zones = get_data("ZONE_PERFORMANCE")
    routes = get_data("ROUTE_POPULARITY")

    if has(zones, "zone", "trips"):
        top = zones.sort_values("trips", ascending=False).iloc[0]
        total_trips = zones["trips"].sum()
        share = top["trips"] / total_trips * 100 if total_trips else 0
        top10_share = zones.nlargest(10, "trips")["trips"].sum() / total_trips * 100 if total_trips else 0

        c = st.columns(4, gap="medium")
        with c[0]:
            kpi_card("Pickup Zones", f"{zones['zone'].nunique():,}", "📍", "Active zones", accent=YELLOW)
        with c[1]:
            kpi_card("Zone Trips", compact(total_trips), "🚕", "Across all zones", accent=TEAL)
        with c[2]:
            kpi_card("Top Zone", str(top["zone"]), "🏆", f"{share:.1f}% of all trips", accent=VIOLET, small=True)
        with c[3]:
            kpi_card("Top-10 Concentration", f"{top10_share:.1f}%", "🎯", "Share of trips from 10 zones", accent=CORAL)

        st.write("")
        left, right = st.columns(2, gap="medium")
        with left:
            section_title("Top Pickup Zones", "By trip volume")
            t = zones.nlargest(12, "trips").sort_values("trips")
            fig = px.bar(t, x="trips", y="zone", orientation="h", color="trips",
                         color_continuous_scale=SEQ_YELLOW, text=t["trips"].map(compact),
                         labels={"trips": "Trips", "zone": ""})
            fig.update_traces(textposition="outside", textfont=dict(color=TEXT), cliponaxis=False)
            show_chart(fig, "zn_top", 430)
        with right:
            if "total_revenue" in zones.columns:
                section_title("Revenue by Zone", "Top 12 by revenue")
                t = zones.nlargest(12, "total_revenue").sort_values("total_revenue")
                fig = px.bar(t, x="total_revenue", y="zone", orientation="h", color="total_revenue",
                             color_continuous_scale=SEQ_TEAL,
                             text=t["total_revenue"].map(lambda v: compact(v, "$")),
                             labels={"total_revenue": "Revenue ($)", "zone": ""})
                fig.update_traces(textposition="outside", textfont=dict(color=TEXT), cliponaxis=False)
                show_chart(fig, "zn_rev", 430)

        if "borough" in zones.columns:
            st.write("")
            b = zones.copy()
            b["borough"] = (b["borough"].fillna("Unknown").astype(str).str.strip()
                            .replace({"N/A": "Unknown", "": "Unknown"}))
            l2, r2 = st.columns(2, gap="medium")
            with l2:
                section_title("Trips by Borough", "Share of all pickups · small boroughs grouped as Other")
                share_bars(b, "borough", "trips", "zn_borough_trips", 340, color=YELLOW, min_pct=1.0)
            with r2:
                if "total_revenue" in b.columns:
                    section_title("Revenue by Borough", "Share of total revenue")
                    share_bars(b, "borough", "total_revenue", "zn_borough_rev", 340,
                               value_prefix="$", color=TEAL, min_pct=1.0)

        with st.expander("Explore zone performance data"):
            st.dataframe(zones, use_container_width=True, hide_index=True)

    if not routes.empty:
        st.write("")
        section_title("Popular Routes", "Pickup → drop-off pairs ranked by trips")
        q = st.text_input("Search route or zone", placeholder="Type a pickup or drop-off zone…")
        rv = routes.copy()
        if q:
            mask = pd.Series(False, index=rv.index)
            for col in ("pickup_zone", "dropoff_zone"):
                if col in rv.columns:
                    mask |= rv[col].astype(str).str.contains(q, case=False, na=False)
            rv = rv[mask]
        cfg = {}
        if "trips" in rv.columns:
            rv = rv.sort_values("trips", ascending=False)
            cfg["trips"] = st.column_config.ProgressColumn(
                "Trips", format="%d", min_value=0, max_value=int(max(rv["trips"].max(), 1)))
        st.dataframe(rv, use_container_width=True, hide_index=True, column_config=cfg)
    elif zones.empty:
        st.info("No zone or route data is available.")


# ───────────────────────── 4. Revenue & Payments ─────────────────────────
elif page.endswith("Revenue & Payments"):
    page_header("FINANCIAL INTELLIGENCE", "Revenue & Payments",
                "Revenue patterns, payment preferences and tipping behaviour.")

    payments = get_data("PAYMENT_ANALYSIS")
    monthly = get_data("MONTHLY_SUMMARY")

    if has(payments, "payment_type_desc", "trips"):
        total_trips = payments["trips"].sum()
        total_rev = payments["total_revenue"].sum() if "total_revenue" in payments.columns else float("nan")
        avg_tip = payments["avg_tip_amount"].mean() if "avg_tip_amount" in payments.columns else float("nan")
        top = payments.sort_values("trips", ascending=False).iloc[0]
        top_share = top["trips"] / total_trips * 100 if total_trips else 0

        c = st.columns(4, gap="medium")
        with c[0]:
            kpi_card("Trips Analyzed", compact(total_trips), "🚕", "All payment types", accent=YELLOW)
        with c[1]:
            kpi_card("Recorded Revenue", compact(total_rev, "$"), "💵", "Summed by payment type", accent=TEAL)
        with c[2]:
            kpi_card("Average Tip", money(avg_tip), "🤝", "Mean tip amount", accent=VIOLET)
        with c[3]:
            kpi_card("Leading Payment", str(top["payment_type_desc"]), "💳",
                     f"{top_share:.1f}% of trips", accent=CORAL, small=True)

        st.write("")
        left, right = st.columns(2, gap="medium")
        with left:
            section_title("Trips by Payment Type", "Share of recorded trips")
            share_bars(payments, "payment_type_desc", "trips", "pay_share", 380, color=YELLOW)
        with right:
            if "total_revenue" in payments.columns:
                section_title("Revenue by Payment Type", "Total revenue per category")
                p = payments.sort_values("total_revenue")
                fig = px.bar(p, x="total_revenue", y="payment_type_desc", orientation="h",
                             color="total_revenue", color_continuous_scale=SEQ_TEAL,
                             text=p["total_revenue"].map(lambda v: compact(v, "$")),
                             labels={"total_revenue": "Revenue ($)", "payment_type_desc": ""})
                fig.update_traces(textposition="outside", textfont=dict(color=TEXT), cliponaxis=False)
                show_chart(fig, "pay_rev", 380)

        with st.expander("Payment details"):
            st.dataframe(payments, use_container_width=True, hide_index=True)

    if has(monthly, "pickup_month", "total_revenue"):
        monthly["pickup_month"] = pd.to_datetime(monthly["pickup_month"], errors="coerce")
        monthly = monthly.dropna(subset=["pickup_month"]).sort_values("pickup_month")
        if not monthly.empty:
            st.write("")
            section_title("Monthly Revenue Trend", "Revenue movement over time")
            fig = px.area(monthly, x="pickup_month", y="total_revenue", markers=True,
                          color_discrete_sequence=[YELLOW],
                          labels={"pickup_month": "", "total_revenue": "Revenue ($)"})
            fig.update_traces(line=dict(width=3), fillcolor="rgba(245,180,0,.18)")
            show_chart(fig, "pay_monthly")

            if "revenue_mom_pct" in monthly.columns:
                section_title("Month-over-Month Change", "Green = growth, red = decline")
                m = monthly.dropna(subset=["revenue_mom_pct"])
                fig = go.Figure(go.Bar(
                    x=m["pickup_month"], y=m["revenue_mom_pct"],
                    marker_color=[GREEN if v >= 0 else CORAL for v in m["revenue_mom_pct"]],
                    text=[f"{v:+.1f}%" for v in m["revenue_mom_pct"]],
                    textposition="outside", textfont=dict(color=TEXT)))
                show_chart(fig, "pay_mom")


# ───────────────────────── 5. Data Quality ─────────────────────────
else:
    page_header("PLATFORM OBSERVABILITY", "Data Quality & Pipeline Health",
                "File-level volumes, rejected records and cleaning efficiency.")

    quality = get_data("DATA_QUALITY_BY_FILE")

    if not quality.empty:
        bronze = quality["bronze_rows"].sum() if "bronze_rows" in quality.columns else 0
        silver = quality["silver_rows"].sum() if "silver_rows" in quality.columns else 0
        rejected = quality["rejected_rows"].sum() if "rejected_rows" in quality.columns else 0
        rate = rejected / bronze * 100 if bronze else 0
        status = ("ok", "HEALTHY") if rate < 5 else ("warn", "REVIEW") if rate < 15 else ("bad", "ATTENTION")

        st.markdown(
            f'Pipeline status: <span class="badge {status[0]}">● {status[1]}</span>',
            unsafe_allow_html=True)
        st.write("")

        c = st.columns(4, gap="medium")
        with c[0]:
            kpi_card("Bronze Rows", compact(bronze), "📥", "Raw rows ingested", accent=YELLOW)
        with c[1]:
            kpi_card("Silver Rows", compact(silver), "🧹", "Clean rows kept", accent=TEAL)
        with c[2]:
            kpi_card("Rejected Rows", compact(rejected), "⚠️", "Removed by cleaning rules", accent=CORAL)
        with c[3]:
            kpi_card("Rejection Rate", f"{rate:.2f}%", "🛡️", "Rejected ÷ Bronze", accent=VIOLET)

        st.write("")
        left, right = st.columns(2, gap="medium")
        cols = [c_ for c_ in ("bronze_rows", "silver_rows", "rejected_rows") if c_ in quality.columns]

        with left:
            if cols and "source_file" in quality.columns:
                section_title("Rows by Source File", "Bronze vs. Silver vs. Rejected")
                melted = quality.melt(id_vars="source_file", value_vars=cols,
                                      var_name="layer", value_name="rows")
                fig = px.bar(melted, x="source_file", y="rows", color="layer", barmode="group",
                             color_discrete_map={"bronze_rows": YELLOW, "silver_rows": TEAL,
                                                 "rejected_rows": CORAL},
                             labels={"source_file": "", "rows": "Rows", "layer": ""})
                show_chart(fig, "q_rows", 380)
        with right:
            if has(quality, "rejected_pct", "source_file"):
                section_title("Rejection Rate by File", "Percentage reported by the Gold model")
                r = quality.sort_values("rejected_pct")
                fig = px.bar(r, x="rejected_pct", y="source_file", orientation="h",
                             color="rejected_pct", color_continuous_scale=["#FEE2E2", "#FB7185", "#BE123C"],
                             text=r["rejected_pct"].map(lambda v: f"{v:.2f}%"),
                             labels={"rejected_pct": "Rejected (%)", "source_file": ""})
                fig.update_traces(textposition="outside", textfont=dict(color=TEXT), cliponaxis=False)
                show_chart(fig, "q_rate", 380)

        with st.expander("Explore file quality records"):
            st.dataframe(quality, use_container_width=True, hide_index=True)

        if "loaded_at" in quality.columns:
            loaded = pd.to_datetime(quality["loaded_at"], errors="coerce").max()
            if pd.notna(loaded):
                st.caption(f"Latest load timestamp: {loaded}")
    else:
        st.info("No file-level data quality records are available.")


st.markdown(
    """<div class="footer">NYC TAXI ANALYTICS · Snowflake + dbt Gold models
    <span style="float:right">Cache: 5 minutes</span></div>""",
    unsafe_allow_html=True,
)