#!/bin/bash
# Live demo: Cases 1 and 2 on the three VMs, snapshots at three times, then heat maps.
# Run from the repo root on heat-ali:  bash scripts/demo.sh
# Optional environment: N (64), P (8), DECOMP (blocks), STEPLIST ("20 150 1000").
N=${N:-64}; P=${P:-8}; DECOMP=${DECOMP:-blocks}; STEPLIST=${STEPLIST:-"20 150 1000"}
RUN="mpirun --hostfile hosts --map-by slot -np $P --mca oob_tcp_if_include tailscale0 --mca btl_tcp_if_include tailscale0 --mca btl tcp,self"
mkdir -p /tmp/demo
echo "== where the $P processes run =="
$RUN hostname | sort | uniq -c
for kase in 1 2; do
  for s in $STEPLIST; do
    echo "== case $kase, $s steps =="
    $RUN ./heat --decomp $DECOMP --case $kase --N $N --r 0.24 --steps $s --out /tmp/demo/case${kase}_s${s}.bin | tail -1
  done
done
python3 scripts/plot_demo.py $N 0.24 $STEPLIST
