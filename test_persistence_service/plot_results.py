import pandas as pd
import matplotlib.pyplot as plt
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────
USER_LEVELS = [10, 25, 50, 100, 200]
RESULTS_DIR = "."
# ─────────────────────────────────────────────────────────────────────────────

summary = []
per_ep  = []

for u in USER_LEVELS:
    path = os.path.join(RESULTS_DIR, f"results_{u}users_stats.csv")
    if not os.path.exists(path):
        print(f"WARNING: {path} not found — skipping")
        continue

    df  = pd.read_csv(path)
    agg = df[df["Name"] == "Aggregated"].iloc[0]
    total = agg["Request Count"]
    fails = agg["Failure Count"]

    summary.append({
        "users":     u,
        "rps":       agg["Requests/s"],
        "avg_rt":    agg["Average Response Time"],
        "p50":       agg["50%"],
        "p95":       agg["95%"],
        "p99":       agg["99%"],
        "error_pct": (fails / total * 100) if total > 0 else 0,
    })

    for _, row in df[df["Name"] != "Aggregated"].iterrows():
        per_ep.append({
            "users":    u,
            "endpoint": row["Name"],
            "avg_rt":   row["Average Response Time"],
            "p95":      row["95%"],
            "rps":      row["Requests/s"],
        })

df_sum = pd.DataFrame(summary)
df_ep  = pd.DataFrame(per_ep)

if df_sum.empty:
    print("No CSV files found. Run the benchmark first.")
    exit()

print(f"Loaded {len(df_sum)} user levels: {df_sum['users'].tolist()}")

# ── PLOT 1: Average Response Time ─────────────────────────────────────────────
plt.figure(figsize=(8, 5))
plt.plot(df_sum["users"], df_sum["avg_rt"], marker="o", color="steelblue",
         linewidth=2.5, label="Avg Response Time")
plt.xlabel("Concurrent Users")
plt.ylabel("Response Time (ms)")
plt.title("Persistence: Avg Response Time vs Load")
plt.xticks(USER_LEVELS)
plt.legend()
plt.tight_layout()
plt.savefig("plot_response_time.png", dpi=150)
print("Saved: plot_response_time.png")

# ── PLOT 2: Throughput ────────────────────────────────────────────────────────
plt.figure(figsize=(8, 5))
plt.plot(df_sum["users"], df_sum["rps"], marker="o", color="seagreen",
         linewidth=2.5, label="Throughput (req/s)")
plt.xlabel("Concurrent Users")
plt.ylabel("Requests / Second")
plt.title("Persistence: Throughput vs Load")
plt.xticks(USER_LEVELS)
plt.legend()
plt.tight_layout()
plt.savefig("plot_throughput.png", dpi=150)
print("Saved: plot_throughput.png")

# ── PLOT 3: Latency Percentiles ───────────────────────────────────────────────
plt.figure(figsize=(8, 5))
plt.plot(df_sum["users"], df_sum["p50"], marker="o", linewidth=2.5, label="p50 (median)")
plt.plot(df_sum["users"], df_sum["p95"], marker="s", linewidth=2.5, label="p95")
plt.plot(df_sum["users"], df_sum["p99"], marker="^", linewidth=2.5, label="p99")
plt.xlabel("Concurrent Users")
plt.ylabel("Response Time (ms)")
plt.title("Persistence: Latency Percentiles vs Load")
plt.xticks(USER_LEVELS)
plt.legend()
plt.tight_layout()
plt.savefig("plot_percentiles.png", dpi=150)
print("Saved: plot_percentiles.png")

# ── PLOT 4: Error Rate ────────────────────────────────────────────────────────
plt.figure(figsize=(8, 5))
plt.plot(df_sum["users"], df_sum["error_pct"], marker="o", color="crimson",
         linewidth=2.5, label="Error Rate %")
plt.xlabel("Concurrent Users")
plt.ylabel("Error Rate (%)")
plt.title("Persistence: Error Rate vs Load")
plt.xticks(USER_LEVELS)
plt.legend()
plt.tight_layout()
plt.savefig("plot_error_rate.png", dpi=150)
print("Saved: plot_error_rate.png")

# ── PLOT 5: Per-Endpoint Response Time ───────────────────────────────────────
if not df_ep.empty:
    pivot = df_ep.pivot(index="users", columns="endpoint", values="avg_rt")
    ax = pivot.plot(kind="bar", figsize=(12, 6), width=0.75)
    ax.set_xlabel("Concurrent Users")
    ax.set_ylabel("Avg Response Time (ms)")
    ax.set_title("Persistence: Per-Endpoint Response Time vs Load")
    ax.set_xticklabels([str(u) for u in pivot.index], rotation=0)
    ax.legend(loc="upper left", fontsize=9)
    plt.tight_layout()
    plt.savefig("plot_per_endpoint.png", dpi=150)
    print("Saved: plot_per_endpoint.png")

# ── PLOT 6: Read vs Write Latency ─────────────────────────────────────────────
if not df_ep.empty:
    reads  = ["GET /users/[id]", "GET /products/[id]", "GET /orders/user/[id]"]
    writes = ["POST /orders", "POST /orderitems"]

    read_avg  = df_ep[df_ep["endpoint"].isin(reads)].groupby("users")["avg_rt"].mean()
    write_avg = df_ep[df_ep["endpoint"].isin(writes)].groupby("users")["avg_rt"].mean()

    plt.figure(figsize=(8, 5))
    plt.plot(read_avg.index,  read_avg.values,  marker="o", linewidth=2.5,
             color="steelblue", label="Reads (avg of GETs)")
    plt.plot(write_avg.index, write_avg.values, marker="s", linewidth=2.5,
             color="crimson", label="Writes (avg of POSTs)")
    plt.xlabel("Concurrent Users")
    plt.ylabel("Avg Response Time (ms)")
    plt.title("Persistence: Read vs Write Latency vs Load")
    plt.xticks(USER_LEVELS)
    plt.legend()
    plt.tight_layout()
    plt.savefig("plot_read_vs_write.png", dpi=150)
    print("Saved: plot_read_vs_write.png")

# ── METRIC SUMMARY TABLE ──────────────────────────────────────────────────────
print("\n── Benchmark Summary ──────────────────────────────────────────")
print(df_sum.to_string(index=False))

# Key derived metrics
print("\n── Key Metrics ────────────────────────────────────────────────")
baseline = df_sum[df_sum["users"] == df_sum["users"].min()].iloc[0]
peak     = df_sum[df_sum["users"] == df_sum["users"].max()].iloc[0]

rt_degradation = ((peak["avg_rt"] - baseline["avg_rt"]) / baseline["avg_rt"]) * 100
throughput_gain = ((peak["rps"] - baseline["rps"]) / baseline["rps"]) * 100

print(f"Baseline avg RT  ({int(baseline['users'])} users): {baseline['avg_rt']:.1f} ms")
print(f"Peak avg RT      ({int(peak['users'])} users): {peak['avg_rt']:.1f} ms")
print(f"RT degradation:  {rt_degradation:.1f}%")
print(f"Throughput gain: {throughput_gain:.1f}%  ({baseline['rps']:.1f} → {peak['rps']:.1f} req/s)")

if not df_ep.empty:
    avg_read  = df_ep[df_ep["endpoint"].isin(reads)]["avg_rt"].mean()
    avg_write = df_ep[df_ep["endpoint"].isin(writes)]["avg_rt"].mean()
    print(f"Avg read latency:  {avg_read:.1f} ms")
    print(f"Avg write latency: {avg_write:.1f} ms")
    print(f"Write/Read ratio:  {avg_write/avg_read:.1f}x slower")

print("\nAll plots complete.")