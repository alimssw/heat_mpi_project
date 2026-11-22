"""Task 3.2(c): numerical check of the three-point second derivative.

D2 f(x) = (f(x-h) - 2 f(x) + f(x+h)) / h^2, tested on f = sin at x = 1,
where the exact value is f''(1) = -sin(1).
Prints the error, the ratio of successive errors, and the observed order
p = log2(ratio), in the style of the table in Section 3.4.
"""
import math

x = 1.0
exact = -math.sin(x)
predicted_lead = lambda h: h**2 / 12 * math.sin(x)  # h^2/12 * f''''(1), f'''' = sin

print(f"{'h':>8} {'D2 f(1)':>20} {'|D2 f - f2|':>13} {'ratio':>7} {'p_obs':>6} {'h^2/12 sin1':>13}")
prev = None
for k in range(4):
    h = 0.1 / 2**k
    d2 = (math.sin(x - h) - 2 * math.sin(x) + math.sin(x + h)) / h**2
    err = abs(d2 - exact)
    if prev is None:
        ratio_s, p_s = "—", "—"
    else:
        ratio = prev / err
        ratio_s, p_s = f"{ratio:.2f}", f"{math.log2(ratio):.2f}"
    print(f"{h:>8.4f} {d2:>20.12f} {err:>13.3e} {ratio_s:>7} {p_s:>6} {predicted_lead(h):>13.3e}")
    prev = err
