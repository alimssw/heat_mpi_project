# Latency and bandwidth (Part 0, step 6)

Fitted with scripts/fit_network.py: t_s = median one-way time for messages up to 1 KB,
bandwidth = 1 / slope of a line through the 1 MB to 16 MB points. Raw fits: network_table.md.

| Connection | Latency t_s | Bandwidth | Path |
|---|---|---|---|
| heat-ali, same VM (TCP) | 7.84 us | 5335 MB/s | n/a |
| heat-yves, same VM (TCP) | 3.28 us | 7250 MB/s | n/a |
| heat-rael, same VM | 3.48 us | 6333 MB/s | n/a |
| Ali - Yves, runs 1-2 | 58 ms | 0.63 MB/s | DERP (Paris), inferred |
| Ali - Yves, run 3 | 7.84 ms | 0.54 MB/s | direct, inferred |
| Ali - Rael | 109 ms (105 to 174) | 0.48 MB/s | not recorded |
| Yves - Rael | 32 ms (27 to 49) | 0.15 MB/s | not recorded |

Notes
- Same-VM rows for heat-ali and heat-yves use the *_tcp_* reruns (--mca btl tcp,self), the same
  transport as the solver runs. The older pp_same_heat-ali files used shared memory (0.15 us) and
  the older pp_same_heat-yves files are not usable (bandwidth between 13,000 and 250,000 MB/s).
- heat-yves exposes 1 core with 2 threads, so same-VM runs there need --use-hwthread-cpus.
- Ali - Yves path is inferred from latency: tailscale ping on 22 Nov showed DERP (Paris) at about
  115 ms round trip, half of which matches runs 1-2; run 3 matches a direct path.
- Paths for the two Rael links were not recorded when the runs were made.
