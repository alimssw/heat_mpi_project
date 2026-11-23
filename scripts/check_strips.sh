#!/bin/bash
# Compare the strip version against the serial one, byte for byte. Run from the repo root.
fail=0
for N in 16 64 65 100; do
  ./heat --case 2 --N $N --r 0.2 --steps 200 --out /tmp/ref.bin > /dev/null
  for P in 1 2 3 4; do
    mpirun -np $P --oversubscribe --mca btl tcp,self \
      ./heat --decomp strips --case 2 --N $N --r 0.2 --steps 200 --out /tmp/p.bin > /dev/null
    if cmp -s /tmp/ref.bin /tmp/p.bin; then echo "N=$N P=$P identical"
    else echo "N=$N P=$P DIFFERENT"; fail=1; fi
  done
done
exit $fail
