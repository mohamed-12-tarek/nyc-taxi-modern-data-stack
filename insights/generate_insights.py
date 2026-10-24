"""Reads GOLD tables (as ANALYST_ROLE) and produces reports/dashboard.png + reports/summary.md"""
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib 

matplotlib.use("Agg")
import matplotlib.pyplot as plt 
import pandas as pd  

from common.snowflake_conn import get_connection  

REPORTS = PROJECT_ROOT / "reports"
REPORTS.mkdir(exist_ok=True)
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def query(conn, sql: str) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(sql)
    df = pd.DataFrame(cur.fetchall(), columns=[c[0].lower() for c in cur.description])
    for c in df.columns:
        if df[c].map(lambda v: isinstance(v, Decimal)).any():
            df[c] = df[c].astype(float)
    return df


def main() -> None:
    conn = get_connection(role="ANALYST_ROLE", warehouse="ANALYTICS_WH", schema="GOLD")
    try:
        daily = query(conn, "select * from daily_trips order by pickup_date")
        monthly = query(conn, "select * from monthly_summary order by pickup_month")
        hourly = query(conn, "select * from hourly_demand")
        zones = query(conn, "select * from zone_performance order by trips desc limit 10")
        payments = query(conn, "select * from payment_analysis order by trips desc")
        routes = query(conn, "select * from route_popularity order by trips desc limit 10")
        dq = query(conn, "select * from data_quality_by_file")
    finally:
        conn.close()

    if daily.empty:
        print("GOLD is empty - nothing to report yet.")
        return

    # KPIs
    trips = int(daily["total_trips"].sum())
    revenue = daily["total_revenue"].sum()
    avg_fare = daily["fare_revenue"].sum() / trips
    avg_miles = daily["total_miles"].sum() / trips
    by_hour = hourly.groupby("pickup_hour")["total_trips"].sum()
    by_dow = hourly.groupby(["day_of_week", "day_name"])["total_trips"].sum().reset_index()
    peak_dow = by_dow.loc[by_dow["total_trips"].idxmax(), "day_name"]
    card = payments[payments["payment_type_desc"] == "Credit card"]
    rejected_pct = 100 * dq["rejected_rows"].sum() / max(dq["bronze_rows"].sum(), 1)

    lines = [
        f"# NYC Yellow Taxi Insights  ({datetime.now():%Y-%m-%d %H:%M})",
        "",
        f"- **Period:** {daily['pickup_date'].min()} -> {daily['pickup_date'].max()}",
        f"- **Total trips:** {trips:,}",
        f"- **Total revenue:** ${revenue:,.0f}",
        f"- **Average fare:** ${avg_fare:,.2f}   |   **Average distance:** {avg_miles:,.2f} miles",
        f"- **Busiest hour:** {int(by_hour.idxmax()):02d}:00   |   **Busiest weekday:** {peak_dow}",
        f"- **Top pickup zone:** {zones.iloc[0]['zone']} ({zones.iloc[0]['borough']}) - {int(zones.iloc[0]['trips']):,} trips",
        f"- **Top route:** {routes.iloc[0]['pickup_zone']} -> {routes.iloc[0]['dropoff_zone']} ({int(routes.iloc[0]['trips']):,} trips)",
    ]
    if not card.empty:
        lines.append(f"- **Average tip (credit card):** {card.iloc[0]['avg_tip_pct']}% of fare")
    lines.append(f"- **Rows rejected by data-quality rules:** {rejected_pct:.2f}% of raw rows")
    (REPORTS / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

    # Dashboard
    fig, ax = plt.subplots(2, 3, figsize=(20, 10))
    fig.suptitle("NYC Yellow Taxi Dashboard", fontsize=17, fontweight="bold")

    d = daily.copy()
    d["pickup_date"] = pd.to_datetime(d["pickup_date"])
    ax[0, 0].plot(d["pickup_date"], d["total_trips"], alpha=0.35, label="Daily")
    ax[0, 0].plot(d["pickup_date"], d["total_trips"].rolling(7, min_periods=1).mean(), linewidth=2, label="7-day avg")
    ax[0, 0].set_title("Daily trips")
    ax[0, 0].legend()
    ax[0, 0].tick_params(axis="x", rotation=30)

    labels = pd.to_datetime(monthly["pickup_month"]).dt.strftime("%Y-%m")
    bars = ax[0, 1].bar(labels, monthly["total_trips"])
    for bar, g in zip(bars, monthly["trips_mom_pct"]):
        if pd.notna(g):
            ax[0, 1].text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{g:+.1f}%", ha="center", va="bottom", fontsize=8)
    ax[0, 1].set_title("Monthly trips (MoM %)")
    ax[0, 1].tick_params(axis="x", rotation=45)

    pivot = (
        hourly.pivot(index="day_of_week", columns="pickup_hour", values="total_trips")
        .reindex(index=range(1, 8), columns=range(24))
        .fillna(0)
    )
    im = ax[0, 2].imshow(pivot.values, aspect="auto", cmap="YlOrRd")
    ax[0, 2].set_yticks(range(7), DAYS)
    ax[0, 2].set_xticks(range(0, 24, 3))
    ax[0, 2].set_title("Demand heatmap (weekday x hour)")
    fig.colorbar(im, ax=ax[0, 2], shrink=0.8)

    ax[1, 0].barh(zones["zone"][::-1], zones["trips"][::-1])
    ax[1, 0].set_title("Top 10 pickup zones")

    ax[1, 1].bar(payments["payment_type_desc"], payments["share_of_trips_pct"])
    for i, row in payments.reset_index(drop=True).iterrows():
        if pd.notna(row["avg_tip_pct"]):
            ax[1, 1].text(i, row["share_of_trips_pct"], f"tip {row['avg_tip_pct']}%", ha="center", va="bottom", fontsize=8)
    ax[1, 1].set_title("Payment mix (% of trips)")
    ax[1, 1].tick_params(axis="x", rotation=30)

    route_labels = (routes["pickup_zone"] + " -> " + routes["dropoff_zone"]).str.slice(0, 38)
    ax[1, 2].barh(route_labels[::-1], routes["trips"][::-1])
    ax[1, 2].set_title("Top 10 routes")
    ax[1, 2].tick_params(axis="y", labelsize=8)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(REPORTS / "dashboard.png", dpi=120)
    print(f"\nSaved: {REPORTS / 'dashboard.png'}")


if __name__ == "__main__":
    main()
