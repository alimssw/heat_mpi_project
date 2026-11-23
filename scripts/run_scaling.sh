#!/bin/bash
# Part 4, experiment 2: strong scaling. Run from the repo root on heat-ali.
#   bash scripts/run_scaling.sh local    # P = 1..4 on this VM only, no network
#   bash scripts/run_scaling.sh slot     # cluster, each VM filled before the next is used
#   bash scripts/run_scaling.sh node     # cluster, processes spread round-robin across VMs
# Optional environment: STEPS (500), REPS (3), NLIST, PLIST, TAG, TIMEOUT (seconds per run).
mode=${1:?usage: run_scaling.sh local|slot|node}
STEPS=${STEPS:-500}; REPS=${REPS:-3}; NLIST=${NLIST:-"512 2048 8192"}
TAG=${TAG:-$(date +%Y-%m-%d_%H%M)}
NET="--mca oob_tcp_if_include tailscale0 --mca btl_tcp_if_include tailscale0 --mca btl tcp,self"
case $mode in
  local) PLIST=${PLIST:-"1 2 3 4"};         WHERE="--host $(hostname):4"; NET="--mca btl tcp,self" ;;
  slot)  PLIST=${PLIST:-"1 2 3 4 5 6 7 8"}; WHERE="--hostfile hosts --map-by slot" ;;
  node)  PLIST=${PLIST:-"1 2 3 4 5 6 7 8"}; WHERE="--hostfile hosts --map-by node" ;;
  *) echo "unknown mode $mode"; exit 1 ;;
esac
out=results/scaling_${mode}_${TAG}.txt
{
  echo "# mode=$mode steps=$STEPS reps=$REPS N=[$NLIST] P=[$PLIST] started $(date -Is)"
  if [ "$mode" != local ]; then
    for peer in heat-yves heat-rael; do
      echo "# path to $peer: $(tailscale ping -c 1 $peer 2>&1 | head -1)"
    done
  fi
} | tee "$out"
for N in $NLIST; do
  for decomp in strips blocks; do
    for P in $PLIST; do
      for rep in $(seq $REPS); do
        line=$(timeout ${TIMEOUT:-1800} mpirun $WHERE -np $P $NET \
                 ./heat --decomp $decomp --case 2 --N $N --r 0.24 --steps $STEPS 2>&1 | tail -1)
        echo "mode=$mode rep=$rep $line" | tee -a "$out"
      done
    done
  done
done
echo "# finished $(date -Is)" | tee -a "$out"
