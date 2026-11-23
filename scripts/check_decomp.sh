#!/bin/bash
# Compare strips and blocks against serial, byte for byte. Run from the repo root.
# Optional argument: a reference binary to produce the serial files (default ./heat).
ref=${1:-./heat}
fail=0
for kase in 2 V; do
  for N in 16 64 65 100; do
    $ref --case $kase --N $N --r 0.2 --steps 200 --out /tmp/ref.bin > /dev/null
    for decomp in strips blocks; do
      for P in 1 2 3 4 6 8; do
        mpirun -np $P --oversubscribe --mca btl tcp,self \
          ./heat --decomp $decomp --case $kase --N $N --r 0.2 --steps 200 --out /tmp/p.bin > /dev/null
        if cmp -s /tmp/ref.bin /tmp/p.bin; then echo "case=$kase N=$N $decomp P=$P identical"
        else echo "case=$kase N=$N $decomp P=$P DIFFERENT"; fail=1; fi
      done
    done
  done
done
[ $fail -eq 0 ] && echo "ALL IDENTICAL" || echo "SOME DIFFER"
exit $fail
