# Task 7.2: convergence table and log-log plot from results/convergence_serial.txt
import math, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rows = []
for line in open("results/convergence_serial.txt"):
    kv = dict(re.findall(r"(\w+)=(\S+)", line))
    rows.append((int(kv["N"]), int(kv["steps"]), float(kv["err_inf"]), float(kv["err_2"])))

print(f"{'N':>5} {'h':>10} {'steps':>6} {'err_inf':>12} {'err_2':>12} {'p_obs':>6}")
prev = None
for N, steps, einf, e2 in rows:
    p = "" if prev is None else f"{math.log2(prev / e2):.3f}"
    print(f"{N:>5} {1 / N:>10.6f} {steps:>6} {einf:>12.4e} {e2:>12.4e} {p:>6}")
    prev = e2

h = [1 / r[0] for r in rows]
e2 = [r[3] for r in rows]
plt.figure(figsize=(5, 4))
plt.loglog(h, e2, "o-", label="measured $||e||_{2,h}$")
plt.loglog(h, [e2[0] * (x / h[0]) ** 2 for x in h], "k--", label="slope 2")
plt.xlabel("h")
plt.ylabel("error at T = 0.05")
plt.title("Test V convergence, r = 0.2")
plt.legend()
plt.grid(True, which="both", alpha=0.3)
plt.tight_layout()
plt.savefig("results/convergence_serial.png", dpi=150)
print("wrote results/convergence_serial.png")
