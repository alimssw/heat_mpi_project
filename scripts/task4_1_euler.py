"""Task 4.1: experiments with forward Euler (and backward Euler) on u' = -lambda u.

u(0) = 1, lambda = 50, t in [0, 1]. Exact solution u(t) = exp(-50 t).
Theory (Section 4.3): forward Euler has g = 1 - lambda*dt and is stable iff dt <= 2/lambda = 0.04.
Backward Euler has g = 1 / (1 + lambda*dt), in (0, 1) for every dt > 0.

Writes three plots: task4_1b_stability.png, task4_1c_convergence.png, task4_1d_backward.png.
"""
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LAM = 50.0
T = 1.0
EXACT_T = math.exp(-LAM * T)


# (a) the two methods, one step at a time -------------------------------------
def forward_euler(dt, t_end=T, lam=LAM):
    """Return the list of times and values u_n, stepping until t_n >= t_end."""
    n_steps = round(t_end / dt)
    ts, us = [0.0], [1.0]
    u = 1.0
    for n in range(n_steps):
        u = u + dt * (-lam * u)          # u_{n+1} = u_n + dt * f(t_n, u_n)
        ts.append((n + 1) * dt)
        us.append(u)
    return ts, us


def backward_euler(dt, t_end=T, lam=LAM):
    """u_{n+1} = u_n + dt * f(t_{n+1}, u_{n+1}) = u_n - lam*dt*u_{n+1}, solved for u_{n+1}."""
    n_steps = round(t_end / dt)
    ts, us = [0.0], [1.0]
    u = 1.0
    for n in range(n_steps):
        u = u / (1.0 + lam * dt)
        ts.append((n + 1) * dt)
        us.append(u)
    return ts, us


# (b) largest dt that does not blow up -----------------------------------------
# Criterion: the numerical solution "blows up" if |u_n| grows, i.e. |u(1)| > |u(0)| = 1.
# dt = 1/n so that t = 1 is reached exactly.
print("(b) forward Euler, scan of dt = 1/n (t = 1 reached exactly)")
print(f"{'n':>4} {'dt':>9} {'g = 1-50dt':>11} {'u_n at t=1':>14}  verdict")
scan = []
for n in range(20, 31):
    dt = 1.0 / n
    _, us = forward_euler(dt)
    u_end = us[-1]
    verdict = "blows up" if abs(u_end) > 1.0 else ("bounded, |u| = 1" if abs(abs(u_end) - 1) < 1e-12 else "decays")
    scan.append((n, dt, u_end))
    print(f"{n:>4} {dt:>9.5f} {1 - LAM*dt:>11.4f} {u_end:>14.4e}  {verdict}")

# finer scan, not tied to t = 1: run 200 steps and watch |u|
print("\n(b) finer scan: 200 steps, growth of |u|")
fine = [0.0390, 0.0395, 0.0399, 0.0400, 0.0401, 0.0405, 0.0410]
print(f"{'dt':>8} {'g':>9} {'|u_200|':>12}")
for dt in fine:
    u = 1.0
    for _ in range(200):
        u = u - LAM * dt * u
    print(f"{dt:>8.4f} {1 - LAM*dt:>9.4f} {abs(u):>12.4e}")

# plot for (b): three time steps around the limit
fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
for dt, col in [(0.038, "#1f5fbf"), (0.040, "#555555"), (0.042, "#c0392b")]:
    ts, us = forward_euler(dt, t_end=1.0)
    ax.plot(ts, us, "o-", ms=3, lw=1, color=col, label=f"Δt = {dt}  (λΔt = {LAM*dt:.2f})")
tt = [k / 400 for k in range(401)]
ax.plot(tt, [math.exp(-LAM * t) for t in tt], color="black", lw=1.5, label="exact  e^(−50t)")
ax.set_xlabel("t"); ax.set_ylabel("u")
ax.set_title("Task 4.1(b): forward Euler, λ = 50, around the limit Δt = 2/λ = 0.04")
ax.title.set_fontsize(10)
ax.set_ylim(-2.5, 2.5)
ax.grid(True, lw=0.4, alpha=0.6)
ax.legend(fontsize=8, loc="lower left")
fig.tight_layout(); fig.savefig("task4_1b_stability.png"); plt.close(fig)

# (c) error at t = 1 for stable time steps --------------------------------------
print("\n(c) forward Euler, error at t = 1 (exact u(1) = e^-50 = %.4e)" % EXACT_T)
print(f"{'dt':>10} {'steps':>8} {'u_n(1)':>12} {'abs error':>11} {'rel error':>10} {'ratio':>7} {'p_obs':>6}")
dts = [1e-2 / 2**k for k in range(0, 11)]
rows = []
prev = None
for dt in dts:
    _, us = forward_euler(dt)
    err = abs(us[-1] - EXACT_T)
    rel = err / EXACT_T
    if prev is None:
        ratio_s = p_s = "—"
    else:
        ratio = prev / err
        ratio_s, p_s = f"{ratio:.3f}", f"{math.log2(ratio):.3f}"
    rows.append((dt, err, rel))
    print(f"{dt:>10.3e} {round(T/dt):>8d} {us[-1]:>12.4e} {err:>11.4e} {rel:>10.4f} {ratio_s:>7} {p_s:>6}")
    prev = err

fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
ax.loglog([r[0] for r in rows], [r[2] for r in rows], "o-", color="#1f5fbf", label="relative error at t = 1")
ref_dt = [rows[-1][0], rows[-4][0]]
c = rows[-1][2] / rows[-1][0]
ax.loglog(ref_dt, [c * d for d in ref_dt], "--", color="#7a7a7a", label="slope 1 reference")
ax.set_xlabel("Δt"); ax.set_ylabel("|u_n(1) − e^(−50)| / e^(−50)")
ax.set_title("Task 4.1(c): forward Euler converges at first order once Δt is small")
ax.title.set_fontsize(10)
ax.grid(True, which="major", lw=0.4, alpha=0.6)
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig("task4_1c_convergence.png"); plt.close(fig)

# (d) backward Euler, same scan as (b) and beyond -------------------------------
print("\n(d) backward Euler, u_n at t = 1")
print(f"{'dt':>8} {'g = 1/(1+50dt)':>15} {'u_n at t=1':>14}")
for dt in [1/40, 1/25, 1/24, 1/20, 1/10, 1/4, 1/2, 1.0]:
    _, us = backward_euler(dt)
    print(f"{dt:>8.4f} {1/(1+LAM*dt):>15.4f} {us[-1]:>14.4e}")

fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
for dt, col in [(0.042, "#c0392b"), (0.1, "#1f5fbf"), (0.25, "#2e8b57")]:
    ts, us = backward_euler(dt)
    ax.plot(ts, us, "o-", ms=3, lw=1, color=col, label=f"backward Euler, Δt = {dt}")
ax.plot(tt, [math.exp(-LAM * t) for t in tt], color="black", lw=1.5, label="exact  e^(−50t)")
ax.set_xlabel("t"); ax.set_ylabel("u")
ax.set_title("Task 4.1(d): backward Euler decays for every Δt, even far above 0.04")
ax.title.set_fontsize(10)
ax.grid(True, lw=0.4, alpha=0.6)
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig("task4_1d_backward.png"); plt.close(fig)
print("\nsaved task4_1b_stability.png, task4_1c_convergence.png, task4_1d_backward.png")
