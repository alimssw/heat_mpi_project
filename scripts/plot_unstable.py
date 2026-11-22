# Task 6.7: Case 1 run 5% above the stability limit (r = 0.2625), at three step counts
import subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

N, r, step_list = 32, 0.2625, [110, 130, 150]
fig, axes = plt.subplots(1, 3, figsize=(13, 4))
for ax, steps in zip(axes, step_list):
    out = f"/tmp/unstable_{steps}.bin"
    subprocess.run(["./heat", "--case", "1", "--N", str(N), "--r", str(r),
                    "--allow-unstable", "1", "--steps", str(steps), "--out", out],
                   check=True, stdout=subprocess.DEVNULL)
    u = np.fromfile(out).reshape(N + 1, N + 1)
    print(f"steps={steps} min={u.min():.4g} max={u.max():.4g}")
    im = ax.imshow(u, origin="lower", extent=[0, 1, 0, 1], cmap="coolwarm")
    ax.set_title(f"{steps} steps: min {u.min():.2g}, max {u.max():.2g}")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.colorbar(im, ax=ax, shrink=0.8)
fig.suptitle(f"Case 1, N = {N}, r = {r} (5% above the limit 0.25)")
fig.tight_layout()
fig.savefig("results/unstable_r0.2625.png", dpi=150)
print("wrote results/unstable_r0.2625.png")
