"""Task 6.7 cross-check: where does the instability first appear?

Independent NumPy implementation of the same explicit update as our C++ solver,
u_new = (1 - 4r) u + r (sum of the 4 neighbours), for Case 1 (all four edges held
at u = 1, interior starts at 0), N = 32, r = 0.2625 (5% above the limit 1/4).

Prints min/max of the field (to compare with our solver), the step at which the
field first leaves the physical range [0, 1], and the size and position of the
checkerboard part |u - average of the 4 neighbours|. Saves snapshots.
"""
import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

N, r, STEPS = 32, 0.2625, 150
u = np.zeros((N + 1, N + 1))          # u[i, j], i along x, j along y
u[0, :] = u[-1, :] = u[:, 0] = u[:, -1] = 1.0

snapshots = {}
first_out = None
print(f"{'step':>5} {'min':>9} {'max':>9} {'max |u - nbr avg|':>18} {'at (i, j)':>10}")
for n in range(1, STEPS + 1):
    new = u.copy()
    new[1:-1, 1:-1] = (1 - 4 * r) * u[1:-1, 1:-1] + r * (
        u[2:, 1:-1] + u[:-2, 1:-1] + u[1:-1, 2:] + u[1:-1, :-2])
    u = new
    inner = u[1:-1, 1:-1]
    if first_out is None and (inner.min() < 0.0 or inner.max() > 1.0):
        first_out = n
        k = np.unravel_index(np.argmax(np.maximum(inner - 1.0, -inner)), inner.shape)
        print(f"   -> field first leaves [0, 1] at step {n}, node (i, j) = ({k[0]+1}, {k[1]+1})")
    if n in (50, 70, 90, 100, 110, 120, 130, 140, 150):
        dev = np.abs(inner - 0.25 * (u[2:, 1:-1] + u[:-2, 1:-1] + u[1:-1, 2:] + u[1:-1, :-2]))
        k = np.unravel_index(np.argmax(dev), dev.shape)
        print(f"{n:>5} {u.min():>9.4f} {u.max():>9.4f} {dev.max():>18.3g} {f'({k[0]+1}, {k[1]+1})':>10}")
    if n in (90, 110, 130, 150):
        snapshots[n] = u.copy()

g_grid = 1 - 8 * r * math.cos(math.pi / (2 * N)) ** 2
print(f"\nworst grid mode: G = {g_grid:.4f}, |G|^20 = {abs(g_grid)**20:.2f}; "
      f"continuous worst |1 - 8r| = {abs(1 - 8*r):.3f}")

fig, axs = plt.subplots(1, 4, figsize=(13, 3.4), dpi=130)
for ax, n in zip(axs, (90, 110, 130, 150)):
    s = snapshots[n]
    dev = np.zeros_like(s)
    dev[1:-1, 1:-1] = np.abs(s[1:-1, 1:-1] - 0.25 * (s[2:, 1:-1] + s[:-2, 1:-1] + s[1:-1, 2:] + s[1:-1, :-2]))
    im = ax.imshow(dev.T, origin="lower", cmap="magma")
    ax.set_title(f"step {n}: |u − neighbour avg|", fontsize=9)
    ax.set_xlabel("i"); ax.set_ylabel("j")
    fig.colorbar(im, ax=ax, fraction=0.046)
fig.suptitle("Task 6.7 (N = 32, r = 0.2625): the checkerboard starts near the corners and spreads inward", fontsize=10)
fig.tight_layout()
fig.savefig("task6_7_onset.png")
print("saved task6_7_onset.png")
