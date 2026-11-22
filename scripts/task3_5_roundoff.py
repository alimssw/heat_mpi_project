"""Task 3.5: where does round-off take over?

Repeats the experiment of Task 3.2(c), D2 f(x) = (f(x-h) - 2 f(x) + f(x+h)) / h^2
for f = sin at x = 1 (exact f''(1) = -sin 1), for h = 1e-1, ..., 1e-10.
Prints the errors, the two terms of the error model, and saves a log-log plot.

Error model (Section 3.8 argument, applied to D2):
  truncation  ~ (h^2 / 12) |f''''(x)|        (Task 3.2(b))
  round-off   ~ 4 eps |f(x)| / h^2           (each of the three values carries a
                                              relative error ~eps; the coefficients
                                              1, -2, 1 have absolute sum 4)
"""
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

x = 1.0
exact = -math.sin(x)
eps = sys.float_info.epsilon  # 2.22e-16 for IEEE double
f_abs = abs(math.sin(x))      # |f(1)| = |f''''(1)| = sin 1

hs = [10.0 ** (-k) for k in range(1, 11)]
errs, trunc, roundoff = [], [], []
print(f"{'h':>8} {'|D2 f - f2|':>13} {'h^2/12 sin1':>13} {'4 eps sin1/h^2':>15}")
for h in hs:
    d2 = (math.sin(x - h) - 2.0 * math.sin(x) + math.sin(x + h)) / (h * h)
    e = abs(d2 - exact)
    t = h * h / 12.0 * f_abs
    ro = 4.0 * eps * f_abs / (h * h)
    errs.append(e); trunc.append(t); roundoff.append(ro)
    print(f"{h:>8.0e} {e:>13.3e} {t:>13.3e} {ro:>15.3e}")

best = min(range(len(hs)), key=lambda k: errs[k])
h_opt = (48.0 * eps) ** 0.25  # minimiser of h^2/12 + 4 eps / h^2 (with |f| = |f''''|)
print(f"\nsmallest measured error: {errs[best]:.3e} at h = {hs[best]:.0e}")
print(f"predicted optimal h = (48 eps)^(1/4) = {h_opt:.2e}, "
      f"predicted minimum error ~ {h_opt**2/12*f_abs + 4*eps*f_abs/h_opt**2:.2e}")

fig, ax = plt.subplots(figsize=(6.4, 4.4), dpi=150)
ax.loglog(hs, errs, "o-", color="#1f5fbf", label="measured error |D2 f(1) - f''(1)|")
ax.loglog(hs, trunc, "--", color="#7a7a7a", label="truncation model  h²/12 · sin 1")
ax.loglog(hs, roundoff, ":", color="#c0392b", label="round-off model  4ε · sin 1 / h²")
ax.axvline(h_opt, color="#999999", lw=0.8)
ax.text(h_opt / 1.3, 1e-12, f"h ≈ (48ε)^¼ ≈ {h_opt:.0e}", fontsize=8, color="#555555", ha="right")
ax.set_xlabel("h")
ax.set_ylabel("error")
ax.set_title("Task 3.5: error of D2 for sin x at x = 1")
ax.set_ylim(1e-13, 1e5)
ax.grid(True, which="major", lw=0.4, alpha=0.6)
ax.legend(fontsize=8, loc="upper center")
fig.tight_layout()
fig.savefig("task3_5_roundoff.png")
print("saved task3_5_roundoff.png")
