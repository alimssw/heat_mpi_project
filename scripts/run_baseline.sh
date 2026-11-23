#!/bin/bash
# Part 4, experiment 1: serial run time on this VM. Run from the repo root, on each VM.
out=results/baseline_$(hostname).txt
: > "$out"
for N in 512 1024 2048 4096 8192; do
  for rep in 1 2 3; do
    ./heat --case 2 --N $N --r 0.24 --steps 500 | tee -a "$out"
  done
done
