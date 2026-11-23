#!/bin/bash
# Part 4, experiment 2: strong scaling. Run from the repo root on heat-ali.
#   bash scripts/run_scaling.sh local    # P = 1..4 on this VM only, no network, 500 steps
#   bash scripts/run_scaling.sh slot     # cluster, each VM filled before the next is used, 100 steps
#   bash scripts/run_scaling.sh node     # cluster, processes spread round-robin across VMs, 100 steps
# Blocks are run only at P = 4, 6, 8: for other P, MPI_Dims_create gives a grid one block wide,
# which is the strip layout (set BLOCKS_ALL=1 to run them anyway).
# Optional environment: STEPS, REPS (3), NLIST, PLIST, TAG, TIMEOUT (seconds per run).
mode=${1:?usage: run_scaling.sh local|slot|node}
REPS=${REPS:-3}; NLIST=${NLIST:-"512 2048 8192"}
TAG=${TAG:-$(date +%Y-%m-%d_%H%M)}
NET="--mca oob_tcp_if_include tailscale0 --mca btl_tcp_if_include tailscale0 --mca btl tcp,self"
case $mode in
  local) PLIST=${PLIST:-"1 2 3 4"}; STEPS=${STEPS:-500}; WHERE="--host $(hostname):4"; NET="--mca btl tcp,self" ;;
  slot)  PLIST=${PLIST:-"1 2 3 4 5 6 7 8"}; STEPS=${STEPS:-100}; WHERE="--hostfile hosts --map-by slot" ;;
  node)  PLIST=${PLIST:-"1 2 3 4 5 6 7 8"}; STEPS=${STEPS:-100}; WHERE="--hostfile hosts --map-by node" ;;
  *) echo "unknown mode $mode"; exit 1 ;;
esac
out=results/scaling_${mode}_${TAG}.txt
paths() {
  for peer in heat-yves heat-rael; do
    echo "# $(date -Is) path to $peer: $(tailscale ping -c 1 $peer 2>&1 | head -1)"
  done
}
echo "# mode=$mode steps=$STEPS reps=$REPS N=[$NLIST] P=[$PLIST] started $(date -Is)" | tee "$out"
for N in $NLIST; do
  [ "$mode" != local ] && paths | tee -a "$out"
  for decomp in strips blocks; do
    for P in $PLIST; do
      if [ $decomp = blocks ] && [ -z "$BLOCKS_ALL" ]; then
        case $P in 4|6|8) ;; *) continue ;; esac
      fi
      for rep in $(seq $REPS); do
        line=$(timeout ${TIMEOUT:-900} mpirun $WHERE -np $P $NET \
                 ./heat --decomp $decomp --case 2 --N $N --r 0.24 --steps $STEPS 2>&1 | tail -1)
        echo "mode=$mode rep=$rep $line" | tee -a "$out"
      done
    done
  done
done
echo "# finished $(date -Is)" | tee -a "$out"
