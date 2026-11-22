# Parallel 2D heat diffusion with MPI over Tailscale

Explicit finite-difference solver for the 2D heat equation on the unit square, run on a
cluster of three Ubuntu VMs (heat-ali, heat-yves, heat-rael) joined by Tailscale.

## Build

On every VM, in the repository root (same path on every VM: `~/heat`):

    make

This builds `heat`, `hello` and `pingpong` with `mpicxx -std=c++17 -O2 -ffp-contract=off`.
`make clean` removes them.

## Run on one VM

    ./heat --case V --N 64 --r 0.2 --T 0.05
    ./heat --case 2 --N 1024 --r 0.2 --steps 500 --out u.bin

## Options

| Option | Meaning | Default |
|---|---|---|
| `--case` | `1` (four hot edges), `2` (hot top and bottom), `V` (verification test) | `V` |
| `--N` | number of intervals per direction; the grid has (N+1) x (N+1) nodes | `64` |
| `--r` | alpha*dt/h^2; must satisfy 0 < r <= 0.25 or the program refuses to run | `0.2` |
| `--steps` | fixed number of time steps | none |
| `--T` | final time; the step count is rounded up so T/dt is an integer and r is not exceeded | none |
| `--out` | output file for the final field (optional) | none |
| `--decomp` | `serial` (strips and blocks are not implemented yet) | `serial` |
| `--allow-unstable 1` | permit r > 0.25, used only for Task 6.7 | off |

One of `--steps` or `--T` is required.

## Output

Standard output is one summary line in key=value form, for example

    decomp=serial P=1 N=64 r=0.2 steps=1024 T=0.05 t_total=0.002568 t_comp=0.002568 t_comm=0 err_inf=1.034425e-04 err_2=5.172124e-05

`err_inf` and `err_2` appear only for `--case V`. Times are for the time-stepping loop only.

The `--out` file holds the full (N+1) x (N+1) grid, boundary included, as raw little-endian
doubles in row-major order (row j is the line y = j*h; i varies fastest), with no header.

## Run on the cluster

The hostfile `hosts` lists the VMs and their slots. Always tell Open MPI to use the Tailscale
interface:

    mpirun --hostfile hosts -np 8 \
           --mca oob_tcp_if_include tailscale0 \
           --mca btl_tcp_if_include tailscale0 \
           --mca btl tcp,self \
           ./hello

heat-yves exposes 1 core with 2 threads, so a run on that VM alone with 2 processes needs
`--use-hwthread-cpus`.

## Network measurements

    mpirun -np 2 --mca btl tcp,self ./pingpong > results/pp_same_<host>_tcp_run1.csv
    python3 scripts/fit_network.py

`pingpong` prints `bytes,one_way_seconds,reps` for message sizes from 8 B to 16 MB.
`fit_network.py` fits latency and bandwidth for every connection and writes
`results/network_table.md`. The curated table is `results/network_summary.md`.

## Verification

    for N in 16 32 64 128 256; do ./heat --case V --N $N --r 0.2 --T 0.05; done > results/convergence_serial.txt
    python3 scripts/plot_convergence.py     # table and results/convergence_serial.png
    python3 scripts/plot_unstable.py        # Task 6.7, results/unstable_r0.2625.png

## Repository layout

- `heat.cpp`: the solver
- `hello.cpp`, `pingpong.cpp`: cluster test and network benchmark
- `hosts`: example hostfile
- `scripts/`: fitting and plotting scripts
- `results/`: raw measurements, tables and plots
- `llm_log/`: LLM interaction logs
