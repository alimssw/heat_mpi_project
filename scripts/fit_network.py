# Part 0, step 6: fit t_msg(m) = t_s + m * t_w to the ping-pong results.
# t_s (latency) comes from the small messages, bandwidth = 1/t_w from the large ones.
import csv, glob, os, re, statistics
from collections import defaultdict

SMALL_MAX = 1024            # sizes up to 1 KB are used for the latency
LARGE_MIN = 1024 * 1024     # sizes from 1 MB up are used for the bandwidth

def read(path):
    with open(path) as f:
        return [(int(row["bytes"]), float(row["one_way_seconds"])) for row in csv.DictReader(f)]

def fit(data):
    small = [t for m, t in data if m <= SMALL_MAX]
    large = [(m, t) for m, t in data if m >= LARGE_MIN]
    t_s = statistics.median(small)
    # least-squares slope through the large-message points
    mm = statistics.mean(m for m, _ in large)
    tm = statistics.mean(t for _, t in large)
    t_w = sum((m - mm) * (t - tm) for m, t in large) / sum((m - mm) ** 2 for m, _ in large)
    return t_s, t_w

groups = defaultdict(list)
for path in sorted(glob.glob("results/pp_*_run*.csv")):
    name = re.sub(r"_run\d+\.csv$", "", os.path.basename(path))
    groups[name].append(path)

def fmt_time(t):
    return f"{t * 1e6:.2f} us" if t < 1e-3 else f"{t * 1e3:.2f} ms"

lines = ["| Connection | Runs | Latency t_s (median) | t_s per run | Bandwidth (median) | Bandwidth per run |",
         "|---|---|---|---|---|---|"]
for name, paths in sorted(groups.items()):
    fits = [fit(read(p)) for p in paths]
    ts = [f[0] for f in fits]
    bw = [1.0 / f[1] / 1e6 if f[1] > 0 else float("nan") for f in fits]   # MB/s
    lines.append(f"| {name[3:]} | {len(paths)} | {fmt_time(statistics.median(ts))} | "
                 f"{', '.join(fmt_time(t) for t in ts)} | {statistics.median(bw):.2f} MB/s | "
                 f"{', '.join(f'{b:.2f}' for b in bw)} |")

table = "\n".join(lines)
print(table)
with open("results/network_table.md", "w") as f:
    f.write(table + "\n")
print("\nwrote results/network_table.md")
