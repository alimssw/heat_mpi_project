# Heat maps for the live demo: reads /tmp/demo/case{1,2}_s{steps}.bin written by scripts/demo.sh
# usage: python3 scripts/plot_demo.py N r steps [steps ...]
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

N, r = int(sys.argv[1]), float(sys.argv[2])
step_list = [int(s) for s in sys.argv[3:]]
dt = r / N**2
names = {1: "Case 1: four hot edges", 2: "Case 2: hot top and bottom, cold sides"}
for kase in (1, 2):
    fig, axes = plt.subplots(1, len(step_list), figsize=(4.6 * len(step_list), 4.4), squeeze=False)
    for ax, steps in zip(axes[0], step_list):
        u = np.fromfile(f"/tmp/demo/case{kase}_s{steps}.bin").reshape(N + 1, N + 1)
        im = ax.imshow(u, origin="lower", extent=[0, 1, 0, 1], cmap="inferno", vmin=0, vmax=1)
        ax.set_title(f"{steps} steps, t = {steps * dt:.4f}\ncentre u = {u[N // 2, N // 2]:.3f}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
    fig.colorbar(im, ax=axes[0].tolist(), shrink=0.85, label="u")
    fig.suptitle(f"{names[kase]} (N = {N}, r = {r})")
    out = f"results/demo_case{kase}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print("wrote", out)
