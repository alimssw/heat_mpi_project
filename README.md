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
| `--decomp` | `serial` (exactly 1 process), `strips` (1D strips) or `blocks` (2D process grid chosen by `MPI_Dims_create`) | `serial` |
| `--allow-unstable 1` | permit r > 0.25, used only for Task 6.7 | off |

One of `--steps` or `--T` is required.

## Output

Standard output is one summary line in key=value form, for example

    decomp=serial P=1 Px=1 Py=1 N=64 r=0.2 steps=1024 T=0.05 t_total=0.002568 t_comp=0.002568 t_comm=0 err_inf=1.034425e-04 err_2=5.172124e-05

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

## Strip and block versions (Parts 2 and 3)

On one VM (heat-ali has 2 cores with 2 threads each, hence the extra flag):

    mpirun -np 4 --use-hwthread-cpus --mca btl tcp,self ./heat --decomp strips --case V --N 256 --r 0.2 --T 0.05

On the cluster:

    mpirun --hostfile hosts -np 8 \
           --mca oob_tcp_if_include tailscale0 --mca btl_tcp_if_include tailscale0 --mca btl tcp,self \
           ./heat --decomp strips --case 2 --N 1024 --r 0.2 --steps 500 --out u.bin

The summary line reports `t_total`, `t_comp` and `t_comm` (halo exchange), each the maximum over ranks.
Use `--decomp blocks` for the 2D block version. The summary line shows the process grid as `Px` and `Py`.
The output file is identical to the serial one for both. To check strips and blocks for P = 1 to 8 and several N:

    bash scripts/check_decomp.sh

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

## Performance study (Part 4)

All runs use Case 2, r = 0.24, a fixed number of steps and three repeats. Run from the repository root.

    bash scripts/run_baseline.sh            # on each VM: serial, N = 512 to 8192 -> results/baseline_<host>.txt
    bash scripts/run_scaling.sh local       # strong scaling, P = 1..4 on this VM, 500 steps
    bash scripts/run_scaling.sh slot        # cluster, each VM filled before the next (--map-by slot), 100 steps
    bash scripts/run_scaling.sh node        # cluster, round-robin across VMs (--map-by node), 100 steps
    bash scripts/run_weak.sh local|slot|node   # weak scaling, about 1024 x 1024 nodes per process

The cluster modes are launched from heat-ali and record the Tailscale path to each VM before every
group of runs. Blocks are run at P = 4, 6, 8 only; for other P the block grid is the strip layout.
Optional environment variables: STEPS, REPS, NLIST, PLIST, TAG, TIMEOUT.

    python3 scripts/analyze_scaling.py      # results/scaling_summary.md and the scaling figures
    python3 scripts/analyze_model.py        # results/model_summary.md, model_vs_measured.png, weak_scaling.png

## Live demo

    bash scripts/demo.sh                    # Cases 1 and 2 on the three VMs, then heat maps

Runs 8 processes with the block layout at N = 64 and writes `results/demo_case1.png` and
`results/demo_case2.png`. Change the run with N, P, DECOMP or STEPLIST, for example
`N=128 P=6 DECOMP=strips bash scripts/demo.sh`.

## Report

`report.pdf` is the project report; `background_notes_solutions.pdf` holds the solutions to the
background notes. `results/fig_decomp.png` is the figure of the two decompositions.
