#!/usr/bin/env python3
"""Part 4: performance model against the measurements, and weak scaling (experiment 3).

Run from the repo root:   python3 scripts/analyze_model.py
Reads   results/baseline_heat-*.txt, the newest results/scaling_{local,slot,node}_*.txt
        and the newest results/weak_{local,slot,node}_*.txt
Writes  results/model_summary.md, results/model_vs_measured.png, results/weak_scaling.png

Model (starts from Task 8.2 of the background notes), time per step:
    T(N, P) = c * (N-1)^2 / P  +  sum over exchange phases of  max over links (t_s + bytes * t_w)
  c     seconds per node update of the slowest VM that holds a process (experiment 1)
  phase one MPI_Sendrecv per direction: 2 phases for strips, 4 for blocks. All processes wait for
        the slowest link of a phase, so a phase costs the worst link, not the average one.
  t_s, t_w  per link, from the Part 0 ping-pong (results/network_summary.md).
With identical links this is exactly Task 8.2: 2 (t_s + N t_w) for strips, 4 (t_s + N t_w / sqrt(P)) for blocks.
"""
import glob, os, re, statistics, sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

KV = re.compile(r"(\w+)=(\S+)")
BLUE, ORANGE = "#257de0", "#f47230"
INK, MUTED, GRID = "#191919", "#666666", "#e3e3e3"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "lines.linewidth": 2, "lines.markersize": 6, "legend.frameon": False})

# ---------------------------------------------------------------- Part 0 parameters
# (latency t_s in seconds, bandwidth in bytes per second), from results/network_summary.md
SAME_VM = (7.84e-6, 5335e6)                       # heat-ali, same VM, TCP
LINK = {frozenset(("heat-ali", "heat-yves")): [7.84e-3, 0.54e6],     # run 3, direct path
        frozenset(("heat-ali", "heat-rael")): [109e-3, 0.48e6],      # measured on a relayed path
        frozenset(("heat-yves", "heat-rael")): [32e-3, 0.15e6]}
SLOTS = [("heat-ali", 4), ("heat-yves", 2), ("heat-rael", 2)]         # the hostfile
REAL = (1e-6, 1e9)   # question 3: a real cluster, t_s = 1 us; 1 GB/s (10 Gb Ethernet) is our assumption


def newest(pattern):
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


def read_runs(path):
    runs = defaultdict(list)
    for line in open(path):
        if line.startswith("#") or "t_total=" not in line:
            continue
        kv = dict(KV.findall(line))
        runs[(kv["decomp"], int(kv["P"]), int(kv["N"]))].append(
            (float(kv["t_total"]) / int(kv["steps"]), float(kv["t_comm"]) / float(kv["t_total"])))
    return {k: {"t": statistics.median(t for t, _ in v), "lo": min(t for t, _ in v),
                "hi": max(t for t, _ in v), "share": statistics.median(s for _, s in v)}
            for k, v in runs.items()}


def session_rtt(peer):
    """Median tailscale round-trip time (seconds) to a peer, recorded during the cluster runs."""
    ms = []
    for path in glob.glob("results/scaling_slot_*.txt") + glob.glob("results/scaling_node_*.txt"):
        for line in open(path):
            m = re.search(rf"path to {peer}: pong .* via (\S+) in (\d+)ms", line)
            if m and "DERP" not in m.group(1):
                ms.append(int(m.group(2)))
    return statistics.median(ms) / 1e3 if ms else None


# The Part 0 Ali - Rael latency (109 ms) was measured on a relayed path. The scaling runs used a
# direct path, so for that one link the model uses half the round-trip time recorded in those runs.
rtt_rael = session_rtt("heat-rael")
if rtt_rael:
    LINK[frozenset(("heat-ali", "heat-rael"))][0] = rtt_rael / 2

# ---------------------------------------------------------------- compute rate (experiment 1)
rate = {}                                         # host -> {N: seconds per node update}
for path in sorted(glob.glob("results/baseline_heat-*.txt")):
    host = os.path.basename(path)[len("baseline_"):-len(".txt")]
    if host.endswith("_throttled"):
        continue
    per_n = defaultdict(list)
    for line in open(path):
        kv = dict(KV.findall(line))
        if "t_total" in kv:
            per_n[int(kv["N"])].append(float(kv["t_total"]) / int(kv["steps"]))
    rate[host] = {N: statistics.median(v) / (N - 1) ** 2 for N, v in per_n.items()}
if not rate:
    sys.exit("no results/baseline_heat-*.txt files found")


def c_of(host, N):
    """Measured seconds per node update on this VM, at the baseline grid size closest to N."""
    table = rate.get(host) or rate["heat-ali"]
    return table[min(table, key=lambda n: abs(n - N))]


# ---------------------------------------------------------------- the model
def hosts_of(mode, P):
    if mode == "local":
        return ["heat-ali"] * P
    if mode == "slot":
        return [h for h, n in SLOTS for _ in range(n)][:P]
    left, out = dict(SLOTS), []                   # node: round-robin over VMs that still have a free slot
    while len(out) < P:
        for h, _ in SLOTS:
            if left[h] > 0 and len(out) < P:
                left[h] -= 1
                out.append(h)
    return out


def dims_of(decomp, P):
    """(Py, Px) as MPI_Dims_create gives them: the most square factorisation, larger factor first."""
    if decomp != "blocks":
        return P, 1
    px = max(d for d in range(1, int(P ** 0.5) + 1) if P % d == 0)
    return P // px, px


def model(N, P, mode, decomp, link=None, c=None):
    """Seconds per time step: (compute, communication)."""
    hosts = hosts_of(mode, P)
    Py, Px = dims_of(decomp, P)
    comp = max((c or c_of(h, N)) for h in hosts) * (N - 1) ** 2 / P

    def cost(a, b, doubles):
        ts, bw = link or (SAME_VM if hosts[a] == hosts[b] else LINK[frozenset((hosts[a], hosts[b]))])
        return ts + 8 * doubles / bw

    row = (N + 1) if Px == 1 else (N - 1) / Px     # strips send whole rows, blocks only their own part
    col = (N - 1) / Py
    up = [cost(cy * Px + cx, (cy + 1) * Px + cx, row) for cy in range(Py - 1) for cx in range(Px)]
    side = [cost(cy * Px + cx, cy * Px + cx + 1, col) for cy in range(Py) for cx in range(Px - 1)]
    comm = 2 * max(up, default=0) + 2 * max(side, default=0)
    return comp, comm


def total(*a, **k):
    return sum(model(*a, **k))


def crossover(f_spread, f_ref, lo=64, hi=10 ** 7):
    """Smallest N at which f_spread(N) < f_ref(N), or None."""
    if f_spread(hi) >= f_ref(hi):
        return None
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (lo, mid) if f_spread(mid) < f_ref(mid) else (mid, hi)
    return hi


strong = {m: read_runs(p) for m in ("local", "slot", "node") if (p := newest(f"results/scaling_{m}_*.txt"))}
weak = {m: read_runs(p) for m in ("local", "slot", "node") if (p := newest(f"results/weak_{m}_*.txt"))}
NAME = {"local": "one VM (heat-ali)", "slot": "cluster, fill one VM first", "node": "cluster, round-robin"}

# ---------------------------------------------------------------- summary
md = ["# Part 4: performance model and weak scaling", "", "Generated by scripts/analyze_model.py.", "",
      "## Model", "",
      "Time per step: `T(N, P) = c (N-1)^2 / P + sum over exchange phases of max over links (t_s + bytes * t_w)`.",
      "Strips have 2 phases per step (up, down), blocks 4 (up, down, left, right). All processes wait for",
      "the slowest link of a phase. With identical links this is Task 8.2:",
      "`2 (t_s + N t_w)` for strips and `4 (t_s + N t_w / sqrt(P))` for blocks.", "",
      "| Link | t_s | Bandwidth (1 / t_w) | Source |", "|---|---|---|---|",
      f"| same VM | {SAME_VM[0] * 1e6:.2f} us | {SAME_VM[1] / 1e6:.0f} MB/s | Part 0, heat-ali, TCP |"]
for pair, (ts, bw) in LINK.items():
    a, b = sorted(pair)
    src = "Part 0"
    if pair == frozenset(("heat-ali", "heat-rael")) and rtt_rael:
        src = "t_s = half the direct round trip recorded in the scaling runs (Part 0 value was relayed); bandwidth from Part 0"
    md.append(f"| {a} - {b} | {ts * 1e3:.3g} ms | {bw / 1e6:.2f} MB/s | {src} |")
md += ["", "Compute rate c: experiment 1, the slowest VM that holds a process, at the nearest baseline grid size.", ""]

for mode, s in strong.items():
    md += [f"## Model against strong scaling: {NAME[mode]}", ""]
    for N in sorted({k[2] for k in s}):
        md += [f"**N = {N}**", "", "| Decomposition | P | Measured ms/step | Model ms/step | Measured / model |",
               "|---|---|---|---|---|"]
        for decomp in ("strips", "blocks"):
            for P in sorted({k[1] for k in s if k[0] == decomp and k[2] == N}):
                if decomp == "blocks" and P not in (4, 6, 8):
                    continue
                t, m = s[(decomp, P, N)]["t"], total(N, P, mode, decomp)
                md.append(f"| {decomp} | {P} | {t * 1e3:.3g} | {m * 1e3:.3g} | {t / m:.2f} |")
        md.append("")

# crossover: all 8 processes on three VMs against staying on heat-ali
md += ["## Does spreading across VMs pay off? (model)", "",
       "Smallest N at which 8 processes on the three VMs (fill one VM first) beat the reference, according",
       "to the model. Two arrays of N x N doubles need 16 N^2 bytes; the three VMs have about 11 GiB in total,",
       "so nothing above N = 27,000 can be run at all.", "",
       "| 8 processes, layout | Beats 1 process from N = | Beats 4 processes on heat-ali from N = |", "|---|---|---|"]
for decomp in ("strips", "blocks"):
    n1 = crossover(lambda N: total(N, 8, "slot", decomp), lambda N: total(N, 1, "local", "strips"))
    n4 = crossover(lambda N: total(N, 8, "slot", decomp), lambda N: total(N, 4, "local", "strips"))
    md.append(f"| {decomp} | " + " | ".join(f"{n:,}" if n else "never (up to 10 million)" for n in (n1, n4)) + " |")
md.append("")

c_ref = c_of("heat-ali", 8192)
md += ["## A real cluster with t_s = 1 us (model prediction)", "",
       f"Every link: t_s = 1 us, bandwidth {REAL[1] / 1e9:.0f} GB/s (assumed, 10 Gb Ethernet); compute rate "
       f"{c_ref * 1e9:.2f} ns per node (heat-ali), 8 real cores.", "",
       "| N | 1 process ms/step | Strips P = 8 | Speed-up | Blocks P = 8 | Speed-up |", "|---|---|---|---|---|---|"]
for N in (512, 2048, 8192):
    t1 = c_ref * (N - 1) ** 2
    ts_, tb_ = (total(N, 8, "slot", d, link=REAL, c=c_ref) for d in ("strips", "blocks"))
    md.append(f"| {N} | {t1 * 1e3:.3g} | {ts_ * 1e3:.3g} | {t1 / ts_:.2f} | {tb_ * 1e3:.3g} | {t1 / tb_:.2f} |")
n_real = crossover(lambda N: total(N, 8, "slot", "strips", link=REAL, c=c_ref), lambda N: c_ref * (N - 1) ** 2, lo=2)
md += ["", f"On such a cluster 8 processes beat 1 from N = {n_real} on.", ""]

for mode, s in weak.items():
    base = s.get(("strips", 1, min(k[2] for k in s)))
    md += [f"## Experiment 3: weak scaling, {NAME[mode]}", "",
           "About 1024 x 1024 nodes per process, N = round(1024 sqrt(P)). Ideal: the time per step stays at the P = 1 value.", "",
           "| Decomposition | P | N | Measured ms/step | Range | T(P) / T(1) | Share | Model ms/step |",
           "|---|---|---|---|---|---|---|---|"]
    for decomp in ("strips", "blocks"):
        for (d, P, N) in sorted(k for k in s if k[0] == decomp):
            r = s[(d, P, N)]
            md.append(f"| {decomp} | {P} | {N} | {r['t'] * 1e3:.3g} | {r['lo'] * 1e3:.3g} to {r['hi'] * 1e3:.3g} | "
                      f"{r['t'] / base['t'] if base else float('nan'):.3g} | {r['share'] * 100:.0f}% | "
                      f"{total(N, P, mode, decomp) * 1e3:.3g} |")
    md.append("")
open("results/model_summary.md", "w").write("\n".join(md))
print("\n".join(md))


# ---------------------------------------------------------------- figures
def curves(ax, s, mode, xs_of):
    """Measured: filled markers (strips joined by a line). Model: dashed line, open markers for blocks."""
    for decomp, colour, mk in (("strips", BLUE, "o"), ("blocks", ORANGE, "s")):
        keys = sorted(k for k in s if k[0] == decomp and (decomp == "strips" or k[1] in (4, 6, 8)))
        if not keys:
            continue
        xs = [k[1] for k in keys]
        ax.plot(xs, [s[k]["t"] for k in keys], color=colour, marker=mk, markeredgecolor="white",
                markeredgewidth=1, linestyle="-" if decomp == "strips" else "none",
                markersize=6 if decomp == "strips" else 8, zorder=3, label=f"{decomp}, measured")
        ax.plot(xs, [total(k[2], k[1], mode, decomp) for k in keys], color=colour, marker=mk,
                markerfacecolor="white", markersize=5, linewidth=1.3,
                linestyle="--" if decomp == "strips" else "none", label=f"{decomp}, model")
    ax.set_yscale("log")
    ax.set_xticks(range(1, 9))


def legend(fig, ax, top):
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.01, top), ncol=4, fontsize=8.5,
               handlelength=3.2, columnspacing=2.2)


rows = [m for m in ("slot", "node") if m in strong]
if rows:
    sizes = sorted({k[2] for m in rows for k in strong[m]})
    fig, axes = plt.subplots(len(rows), len(sizes), figsize=(4.2 * len(sizes), 3.5 * len(rows)),
                             sharex=True, squeeze=False)
    for r, mode in enumerate(rows):
        for c, N in enumerate(sizes):
            ax = axes[r][c]
            curves(ax, {k: v for k, v in strong[mode].items() if k[2] == N}, mode, None)
            ax.set_title(f"N = {N}, {NAME[mode].replace('cluster, ', '')}", loc="left", fontsize=10, fontweight="bold")
            if c == 0:
                ax.set_ylabel("Seconds per time step  (log scale)")
            if r == len(rows) - 1:
                ax.set_xlabel("Processes P")
    legend(fig, axes[0][0], 0.955 if len(rows) > 1 else 0.915)
    fig.suptitle("Model against measurement: the model gets every jump right and stays within a factor of 4",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.text(0.01, 0.005, "Model: measured compute rate plus, per exchange phase, the slowest link's t_s + bytes * t_w "
             "(Part 0). Blocks at P = 4, 6, 8 only. Medians of 3 runs.", color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.02, 1, 0.93 if len(rows) > 1 else 0.88))
    fig.savefig("results/model_vs_measured.png", dpi=150)

if weak:
    order = [m for m in ("local", "slot", "node") if m in weak]
    fig, axes = plt.subplots(1, len(order), figsize=(max(9.5, 4.4 * len(order)), 4), squeeze=False)
    for c, mode in enumerate(order):
        ax, s = axes[0][c], weak[mode]
        curves(ax, s, mode, None)
        base = s.get(("strips", 1, min(k[2] for k in s)))
        if base:
            ax.axhline(base["t"], color=MUTED, linewidth=1)
        ax.set_xticks(sorted({k[1] for k in s}))
        ax.set_xlim(0.7, max(k[1] for k in s) + 0.3)
        ax.set_title(NAME[mode], loc="left", fontsize=10, fontweight="bold")
        ax.set_xlabel("Processes P  (N grows as 1024 sqrt(P))")
        if c == 0:
            ax.set_ylabel("Seconds per time step  (log scale)")
    legend(fig, axes[0][0], 0.915)
    fig.suptitle("Weak scaling, about 1024 x 1024 nodes per process: the time per step does not stay flat",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.text(0.01, 0.005, "Grey line: the ideal, the P = 1 time. Blocks at P = 4, 6, 8 only. Medians of 3 runs.",
             color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.88))
    fig.savefig("results/weak_scaling.png", dpi=150)

print("wrote results/model_summary.md and the PNG figures in results/")
