"""Generate report-quality performance charts from Locust CSV output.

Reads results/image_service/raw/*_stats.csv and produces PNG charts in
results/image_service/graphs/.

Charts:
  1. Response Time vs Load  (avg + median)
  2. Throughput vs Load
  3. Error Rate vs Load     (annotated when 0 %)
  4. SLA Violation Rate     (% requests exceeding 3s threshold)
  5. Tail Latency vs Load   (p95 / p99)
  6. Per-Endpoint Comparison (horizontal bar)
  7. Response Time Over Time (time-series)
  8. Summary Table           (image of tabular data)
"""

import os
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RAW_DIR = "results/image_service/raw"
GRAPHS_DIR = "results/image_service/graphs"
USER_COUNTS = [10, 25, 50, 100, 200]

# ── Style ───────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.figsize": (10, 6),
    "figure.dpi": 150,
    "font.family": "sans-serif",
    "font.size": 12,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.labelsize": 12,
})

BLUE   = "#2563EB"
GREEN  = "#059669"
RED    = "#DC2626"
PURPLE = "#7C3AED"
ORANGE = "#D97706"
GRAY   = "#6B7280"
AMBER  = "#F59E0B"

SLA_THRESHOLD_MS = 3000  # 3 seconds

# ── I/O helpers ─────────────────────────────────────────────────────────────

def load_stats(user_count):
    path = os.path.join(RAW_DIR, f"{user_count}_users_stats.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def load_history(user_count):
    path = os.path.join(RAW_DIR, f"{user_count}_users_stats_history.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def get_aggregated(df):
    agg = df[df["Name"] == "Aggregated"]
    return agg.iloc[0] if not agg.empty else df.iloc[-1]


def estimate_sla_violation_pct(row, threshold_ms=SLA_THRESHOLD_MS):
    """Estimate % of requests exceeding threshold using percentile interpolation.

    Uses the percentile columns from Locust stats CSV to interpolate what
    fraction of requests exceeded the SLA threshold.
    """
    # Percentile breakpoints available in Locust stats CSV
    pct_cols = [
        (50, "50%"), (66, "66%"), (75, "75%"), (80, "80%"),
        (90, "90%"), (95, "95%"), (98, "98%"), (99, "99%"),
        (100, "100%"),
    ]
    # Build (percentile, response_time) pairs
    points = []
    for pct, col in pct_cols:
        val = row.get(col, None)
        if val is not None and not pd.isna(val):
            points.append((pct, float(val)))

    if not points:
        return 0.0

    # If even p100 (max) is below threshold, 0% violated
    if all(rt < threshold_ms for _, rt in points):
        return 0.0
    # If p50 (median) is above threshold, at least 50% violated.
    # Since we don't have percentile data below p50, conservatively
    # estimate that all requests violated the SLA.
    if points[0][1] >= threshold_ms:
        return 100.0

    # Find the two percentile points that bracket the threshold
    for i in range(len(points) - 1):
        p_lo, rt_lo = points[i]
        p_hi, rt_hi = points[i + 1]
        if rt_lo < threshold_ms <= rt_hi:
            # Linear interpolation
            if rt_hi == rt_lo:
                breach_pct = p_lo
            else:
                frac = (threshold_ms - rt_lo) / (rt_hi - rt_lo)
                breach_pct = p_lo + frac * (p_hi - p_lo)
            return 100.0 - breach_pct

    # If threshold is below the minimum percentile we have
    if points[0][1] >= threshold_ms:
        return 100.0
    return 0.0


def collect_metrics():
    rows = []
    for n in USER_COUNTS:
        df = load_stats(n)
        if df is None:
            continue
        r = get_aggregated(df)
        total = max(r.get("Request Count", 1), 1)
        failures = r.get("Failure Count", 0)
        sla_viol = estimate_sla_violation_pct(r, SLA_THRESHOLD_MS)
        rows.append({
            "Users": n,
            "Avg (ms)": r.get("Average Response Time", 0),
            "Median (ms)": r.get("Median Response Time", 0),
            "p95 (ms)": r.get("95%", r.get("95% Response Time", 0)),
            "p99 (ms)": r.get("99%", r.get("99% Response Time", 0)),
            "Max (ms)": r.get("Max Response Time", 0),
            "Req/s": r.get("Requests/s", 0),
            "Failures": int(failures),
            "Total": int(total),
            "Error %": failures / total * 100,
            "SLA Viol %": sla_viol,
        })
    return pd.DataFrame(rows)


def save(fig, name):
    path = os.path.join(GRAPHS_DIR, name)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path}")


# ── Charts ──────────────────────────────────────────────────────────────────

def chart_response_time(m):
    """Avg & median response time vs concurrent users."""
    fig, ax = plt.subplots()
    ax.plot(m["Users"], m["Avg (ms)"],    "o-", color=BLUE,   lw=2, label="Mean")
    ax.plot(m["Users"], m["Median (ms)"], "s--", color=PURPLE, lw=2, label="Median")
    ax.fill_between(m["Users"], m["Avg (ms)"], alpha=0.08, color=BLUE)

    # Annotate each data point with its value
    for _, row in m.iterrows():
        ax.annotate(f'{row["Avg (ms)"]:.0f}',
                    xy=(row["Users"], row["Avg (ms)"]),
                    textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=9, color=BLUE, fontweight="bold")

    ax.set_xlabel("Concurrent Users")
    ax.set_ylabel("Response Time (ms)")
    ax.set_title("Image Provider Service — Response Time vs Load")
    ax.set_xticks(m["Users"])
    ax.legend(loc="upper left")
    save(fig, "response_time_vs_load.png")


def chart_throughput(m):
    """Throughput (req/s) vs concurrent users."""
    fig, ax = plt.subplots()
    ax.plot(m["Users"], m["Req/s"], "s-", color=GREEN, lw=2.5,
            markersize=8, markeredgecolor="white", markeredgewidth=1.5)
    ax.fill_between(m["Users"], m["Req/s"], alpha=0.10, color=GREEN)

    for _, row in m.iterrows():
        ax.annotate(f'{row["Req/s"]:.1f}',
                    xy=(row["Users"], row["Req/s"]),
                    textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=9, color=GREEN, fontweight="bold")

    # Mark peak throughput
    peak_idx = m["Req/s"].idxmax()
    peak = m.iloc[peak_idx]
    ax.annotate(f'Peak: {peak["Req/s"]:.1f} req/s',
                xy=(peak["Users"], peak["Req/s"]),
                textcoords="offset points", xytext=(30, -20),
                ha="center", fontsize=10, color=RED, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.5))

    ax.set_xlabel("Concurrent Users")
    ax.set_ylabel("Throughput (req/s)")
    ax.set_title("Image Provider Service — Throughput vs Load")
    ax.set_xticks(m["Users"])
    ax.set_ylim(bottom=0)
    save(fig, "throughput_vs_load.png")


def chart_error_rate(m):
    """Error rate bar chart — with annotation explaining 0 % result."""
    fig, ax = plt.subplots()
    x_labels = [str(u) for u in m["Users"]]
    bars = ax.bar(x_labels, m["Error %"],
                  color=RED, alpha=0.85, edgecolor="white", lw=1.5)

    # Annotate each bar
    for b, v, total in zip(bars, m["Error %"], m["Total"]):
        label = f"{v:.1f}%\n({int(v * total / 100)}/{total})"
        ax.text(b.get_x() + b.get_width() / 2,
                b.get_height() + 0.3,
                label, ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xlabel("Concurrent Users")
    ax.set_ylabel("Error Rate (%)")
    ax.set_title("Image Provider Service — Error Rate vs Load")

    # If all errors are 0, explain it clearly
    if m["Error %"].max() == 0:
        ax.set_ylim(0, 5)  # Meaningful Y-axis scale
        ax.text(0.5, 0.65,
                "0% HTTP Errors at All Load Levels",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=16, fontweight="bold", color=GRAY, alpha=0.5)
        ax.text(0.5, 0.50,
                "TeaStore degrades with increased latency\n"
                "rather than returning HTTP error codes.\n"
                "At 200 users: avg response = 20.8s, max = 80.8s",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=10, color=GRAY, alpha=0.6,
                linespacing=1.5)
    else:
        ax.set_ylim(bottom=0)

    save(fig, "error_rate_vs_load.png")


def chart_sla_violation(m):
    """SLA violation rate — % of requests exceeding 3s threshold."""
    fig, ax = plt.subplots()
    x_labels = [str(u) for u in m["Users"]]
    vals = m["SLA Viol %"]

    # Color bars: green if <5%, amber if <20%, red if >=20%
    colors = []
    for v in vals:
        if v < 5:
            colors.append(GREEN)
        elif v < 20:
            colors.append(AMBER)
        else:
            colors.append(RED)

    bars = ax.bar(x_labels, vals, color=colors, alpha=0.85,
                  edgecolor="white", lw=1.5)

    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2,
                b.get_height() + 1.0,
                f"{v:.1f}%", ha="center", va="bottom",
                fontsize=11, fontweight="bold")

    # Draw the SLA threshold line concept
    ax.axhline(y=5, color=AMBER, linestyle="--", lw=1.2, alpha=0.6)
    ax.text(len(x_labels) - 0.6, 5.5, "5% warning", fontsize=8,
            color=AMBER, ha="right")
    ax.axhline(y=20, color=RED, linestyle="--", lw=1.2, alpha=0.6)
    ax.text(len(x_labels) - 0.6, 20.5, "20% critical", fontsize=8,
            color=RED, ha="right")

    ax.set_xlabel("Concurrent Users")
    ax.set_ylabel(f"Requests Exceeding {SLA_THRESHOLD_MS}ms (%)")
    ax.set_title(f"Image Provider Service — SLA Violation Rate (>{SLA_THRESHOLD_MS/1000:.0f}s Threshold)")
    ax.set_ylim(0, max(max(vals) * 1.3, 10))
    save(fig, "sla_violation_rate.png")


def chart_tail_latency(m):
    """p95 and p99 tail latency vs concurrent users."""
    fig, ax = plt.subplots()
    ax.plot(m["Users"], m["p95 (ms)"], "^-", color=BLUE, lw=2, label="p95",
            markersize=8, markeredgecolor="white", markeredgewidth=1.5)
    ax.plot(m["Users"], m["p99 (ms)"], "v-", color=RED,  lw=2, label="p99",
            markersize=8, markeredgecolor="white", markeredgewidth=1.5)
    ax.fill_between(m["Users"], m["p95 (ms)"], m["p99 (ms)"],
                    alpha=0.08, color=PURPLE, label="p95–p99 spread")

    for _, row in m.iterrows():
        ax.annotate(f'{row["p99 (ms)"]:.0f}',
                    xy=(row["Users"], row["p99 (ms)"]),
                    textcoords="offset points", xytext=(8, 8),
                    ha="left", fontsize=8, color=RED)

    ax.set_xlabel("Concurrent Users")
    ax.set_ylabel("Response Time (ms)")
    ax.set_title("Image Provider Service — Tail Latency (p95/p99) vs Load")
    ax.set_xticks(m["Users"])
    ax.legend(loc="upper left")
    save(fig, "tail_latency_vs_load.png")


def chart_per_endpoint():
    """Horizontal bar chart comparing endpoints at max load."""
    max_users = max(USER_COUNTS)
    df = load_stats(max_users)
    if df is None:
        return
    ep = df[df["Name"] != "Aggregated"].copy()
    if ep.empty:
        return

    # Clean up endpoint names for readability
    name_map = {
        "/tools.descartes.teastore.webui/category?category=[id]&page=[n]": "Category Page\n(thumbnail grid)",
        "/tools.descartes.teastore.webui/product?id=[id]": "Product Detail\n(full-size image)",
        "/tools.descartes.teastore.webui/home": "Home Page\n(banner images)",
    }
    names = [name_map.get(n, n.split("/")[-1]) for n in ep["Name"]]
    colors = [BLUE, PURPLE, GREEN]

    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.barh(names, ep["Average Response Time"],
                   color=[colors[i % len(colors)] for i in range(len(names))],
                   edgecolor="white", lw=1.5, height=0.5)
    for b, v in zip(bars, ep["Average Response Time"]):
        ax.text(b.get_width() + 200, b.get_y() + b.get_height() / 2,
                f"{v:,.0f} ms ({v/1000:.1f}s)", ha="left", va="center",
                fontsize=10, fontweight="bold")

    ax.set_xlabel("Average Response Time (ms)")
    ax.set_title(f"Image Provider Service — Per-Endpoint Latency ({max_users} Concurrent Users)")
    ax.set_xlim(right=max(ep["Average Response Time"]) * 1.25)
    save(fig, "per_endpoint_comparison.png")


def chart_time_series():
    """Response time over the duration of the highest-load test."""
    max_users = max(USER_COUNTS)
    hist = load_history(max_users)
    if hist is None:
        return
    total = hist[hist["Name"] == "Aggregated"]
    if total.empty:
        total = hist
    col = next((c for c in ["Total Average Response Time",
                             "Average Response Time"] if c in total.columns), None)
    if col is None:
        return

    t = total["Timestamp"].values
    elapsed = t - t[0]
    values = total[col].values

    fig, ax = plt.subplots()
    ax.plot(elapsed, values, color=BLUE, lw=1.8, alpha=0.85)
    ax.fill_between(elapsed, values, alpha=0.08, color=BLUE)

    # Mark the ramp-up completion (200 users / 10 spawn-rate = ~20s)
    ramp_end = 20
    ax.axvline(x=ramp_end, color=ORANGE, linestyle="--", lw=1.5, alpha=0.7)
    ax.annotate("Ramp-up complete\n(200 users)", xy=(ramp_end, max(values) * 0.85),
                textcoords="offset points", xytext=(8, 0),
                fontsize=9, color=ORANGE, fontweight="bold")

    ax.set_xlabel("Elapsed Time (s)")
    ax.set_ylabel("Average Response Time (ms)")
    ax.set_title(f"Image Provider Service — Response Time Over Time ({max_users} Users)")
    save(fig, "response_time_over_time.png")


def chart_summary_table(m):
    """Render a publication-quality summary table as an image."""
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.axis("off")

    col_labels = ["Users", "Avg (ms)", "Median (ms)", "p95 (ms)",
                  "p99 (ms)", "Req/s", "HTTP Err %", "SLA Viol %"]
    table_data = []
    for _, row in m.iterrows():
        table_data.append([
            f'{int(row["Users"])}',
            f'{row["Avg (ms)"]:,.0f}',
            f'{row["Median (ms)"]:,.0f}',
            f'{row["p95 (ms)"]:,.0f}',
            f'{row["p99 (ms)"]:,.0f}',
            f'{row["Req/s"]:.1f}',
            f'{row["Error %"]:.1f}%',
            f'{row["SLA Viol %"]:.1f}%',
        ])

    table = ax.table(cellText=table_data, colLabels=col_labels,
                     cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.6)

    # Style header row
    for j, label in enumerate(col_labels):
        cell = table[0, j]
        cell.set_facecolor("#1F2937")
        cell.set_text_props(color="white", fontweight="bold")

    # Alternate row colors
    for i in range(len(table_data)):
        color = "#F3F4F6" if i % 2 == 0 else "white"
        for j in range(len(col_labels)):
            table[i + 1, j].set_facecolor(color)

    ax.set_title("Image Provider Service — Performance Summary",
                 fontsize=14, fontweight="bold", pad=20)
    save(fig, "summary_table.png")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(GRAPHS_DIR, exist_ok=True)
    m = collect_metrics()
    if m.empty:
        print(f"No data in {RAW_DIR}/. Run tests first: ./run_image_tests.sh")
        sys.exit(1)

    m.to_csv(os.path.join(GRAPHS_DIR, "summary.csv"), index=False)
    print(f"Summary ({len(m)} load levels):\n{m.to_string(index=False)}\n")

    chart_response_time(m)
    chart_throughput(m)
    chart_error_rate(m)
    chart_sla_violation(m)
    chart_tail_latency(m)
    chart_per_endpoint()
    chart_time_series()
    chart_summary_table(m)
    print(f"\nDone. Charts in {GRAPHS_DIR}/")


if __name__ == "__main__":
    main()
