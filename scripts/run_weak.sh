#!/bin/bash
# Part 4, experiment 3: weak scaling. About 1024 x 1024 nodes per process: N = round(1024 * sqrt(P)).
# Run from the repo root on heat-ali.
#   bash scripts/run_weak.sh local    # P = 1..4 on this VM only, 500 steps
#   bash scripts/run_weak.sh slot     # cluster, each VM filled before the next is used, 100 steps
#   bash scripts/run_weak.sh node     # cluster, processes spread round-robin across VMs, 100 steps
# Blocks are run only at P = 4, 6, 8 (for other P the block layout is the strip layout).
# Optional environment: STEPS, REPS (3), PLIST, PER (1024), TAG, TIMEOUT (seconds per run).
mode=${1:?usage: run_weak.sh local|slot|node}
REPS=${REPS:-3}; PER=${PER:-1024}
TAG=${TAG:-$(date +%Y-%m-%d_%H%M)}
NET="--mca oob_tcp_if_include tailscale0 --mca btl_tcp_if_include tailscale0 --mca btl tcp,self"
case $mode in
  local) PLIST=${PLIST:-"1 2 3 4"}; STEPS=${STEPS:-500}; WHERE="--host $(hostname):4"; NET="--mca btl tcp,self" ;;
  slot)  PLIST=${PLIST:-"1 2 3 4 5 6 7 8"}; STEPS=${STEPS:-100}; WHERE="--hostfile hosts --map-by slot" ;;
  node)  PLIST=${PLIST:-"1 2 3 4 5 6 7 8"}; STEPS=${STEPS:-100}; WHERE="--hostfile hosts --map-by node" ;;
  *) echo "unknown mode $mode"; exit 1 ;;
esac
out=results/weak_${mode}_${TAG}.txt
paths() {
  for peer in heat-yves heat-rael; do
    echo "# $(date -Is) path to $peer: $(tailscale ping -c 1 $peer 2>&1 | head -1)"
  done
}
echo "# weak scaling mode=$mode per_process=${PER}x${PER} steps=$STEPS reps=$REPS P=[$PLIST] started $(date -Is)" | tee "$out"
for P in $PLIST; do
  N=$(awk -v p=$P -v n=$PER 'BEGIN{printf "%d", n*sqrt(p)+0.5}')
  [ "$mode" != local ] && paths | tee -a "$out"
  for decomp in strips blocks; do
    if [ $decomp = blocks ]; then
      case $P in 4|6|8) ;; *) continue ;; esac
    fi
    for rep in $(seq $REPS); do
      line=$(timeout --foreground ${TIMEOUT:-900} mpirun $WHERE -np $P $NET \
               ./heat --decomp $decomp --case 2 --N $N --r 0.24 --steps $STEPS 2>&1 | tail -1)
      echo "mode=$mode rep=$rep $line" | tee -a "$out"
    done
  done
done
echo "# finished $(date -Is)" | tee -a "$out"
