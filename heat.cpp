#include <mpi.h>
#include <cmath>
#include <cstdio>
#include <exception>
#include <string>
#include <utility>
#include <vector>

struct Config {
    std::string kase = "V";        // "1", "2" or "V"
    int N = 64;                    // intervals per direction
    double r = 0.2;                // alpha*dt/h^2
    int steps = -1;                // -1 means not given
    double T = -1.0;               // -1 means not given
    std::string out;               // empty means no output file
    std::string decomp = "serial"; // serial or strips
    bool allow_unstable = false;   // Task 6.7 only: run above the stability limit on purpose
};

// Value at global node (i, j) at t = 0. Edge nodes keep this value for the whole run.
static double initial_value(const std::string& kase, int i, int j, int N, double h, double pi) {
    const bool top_bottom = (j == 0 || j == N);
    const bool left_right = (i == 0 || i == N);
    if (kase == "V") return (top_bottom || left_right) ? 0.0 : std::sin(pi * i * h) * std::sin(pi * j * h);
    if (kase == "1") return (top_bottom || left_right) ? 1.0 : 0.0;
    return top_bottom ? 1.0 : 0.0;   // Case 2: hot top and bottom (corners included), cold sides
}

int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    int rank, P;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &P);

    // Print an error once (rank 0), shut MPI down cleanly, and give a failing exit code.
    auto fail = [rank](const std::string& msg) {
        if (rank == 0) std::fprintf(stderr, "error: %s\n", msg.c_str());
        MPI_Finalize();
        return 1;
    };

    // ---- Options ----
    Config c;
    if ((argc - 1) % 2 != 0) return fail("every option needs a value");
    try {
        for (int k = 1; k + 1 < argc; k += 2) {
            std::string key = argv[k], val = argv[k + 1];
            if      (key == "--case")   c.kase = val;
            else if (key == "--N")      c.N = std::stoi(val);
            else if (key == "--r")      c.r = std::stod(val);
            else if (key == "--steps")  c.steps = std::stoi(val);
            else if (key == "--T")      c.T = std::stod(val);
            else if (key == "--out")    c.out = val;
            else if (key == "--decomp") c.decomp = val;
            else if (key == "--allow-unstable") c.allow_unstable = (val == "1");
            else return fail("unknown option " + key);
        }
    } catch (const std::exception&) {
        return fail("an option has a value that is not a number");
    }
    if (c.kase != "1" && c.kase != "2" && c.kase != "V") return fail("--case must be 1, 2 or V");
    if (c.N < 2) return fail("--N must be at least 2");
    if (c.r <= 0.0 || (c.r > 0.25 && !c.allow_unstable))
        return fail("r=" + std::to_string(c.r) + " is unstable. The explicit scheme needs 0 < r <= 0.25.");
    if (c.steps < 0 && c.T < 0.0) return fail("give --steps or --T");
    if (c.decomp == "serial") {
        if (P != 1) return fail("--decomp serial needs exactly 1 process; use --decomp strips with mpirun -np P");
    } else if (c.decomp != "strips") {
        return fail("--decomp " + c.decomp + " is not implemented yet, only serial and strips");
    }

    // ---- Global grid ----
    const int N = c.N;
    const int n = N + 1;                 // nodes per direction, boundary included
    const double h = 1.0 / N;
    const double pi = std::acos(-1.0);
    if (P > N - 1) return fail("more processes than interior rows");

    // ---- Strip decomposition: split the N-1 interior rows (j = 1 .. N-1) among P ranks ----
    // The first (N-1) % P ranks get one extra row.
    const int base = (N - 1) / P, rem = (N - 1) % P;
    auto rows_of  = [base, rem](int p) { return base + (p < rem ? 1 : 0); };
    auto first_of = [base, rem](int p) { return 1 + p * base + (p < rem ? p : rem); };
    const int cnt = rows_of(rank);       // rows this rank owns
    const int j0  = first_of(rank);      // global index of its first owned row
    const int down = (rank > 0)     ? rank - 1 : MPI_PROC_NULL;   // neighbour below (smaller y)
    const int up   = (rank < P - 1) ? rank + 1 : MPI_PROC_NULL;   // neighbour above (larger y)

    // Local storage: rows l = 0 .. cnt+1. Row l holds global row j0 - 1 + l.
    // l = 0 and l = cnt+1 are ghost rows (or the fixed plate edge on the first and last rank).
    auto idx = [n](int i, int l) { return (std::size_t)l * n + i; };
    std::vector<double> u_old((std::size_t)(cnt + 2) * n), u_new;
    for (int l = 0; l <= cnt + 1; ++l)
        for (int i = 0; i <= N; ++i)
            u_old[idx(i, l)] = initial_value(c.kase, i, j0 - 1 + l, N, h, pi);
    u_new = u_old;                       // edge values must be in both arrays

    // ---- Time step. alpha = 1, so dt = r * h^2 ----
    int steps = c.steps;
    double r = c.r;
    if (c.T > 0.0) {   // --T given: choose steps so T/dt is a whole number and r is not exceeded
        steps = (int)std::ceil(c.T / (c.r * h * h));
        r = c.T / steps / (h * h);
    }
    const double dt = r * h * h;
    const double T = steps * dt;

    // ---- Time loop (only this part is timed) ----
    MPI_Barrier(MPI_COMM_WORLD);
    double t_comm = 0.0;
    const double t0 = MPI_Wtime();
    for (int s = 0; s < steps; ++s) {
        // Halo exchange. With MPI_PROC_NULL the call does nothing, so the plate edge stays fixed.
        const double tc = MPI_Wtime();
        MPI_Sendrecv(&u_old[idx(0, cnt)],     n, MPI_DOUBLE, up,   0,    // my top row goes up
                     &u_old[idx(0, 0)],       n, MPI_DOUBLE, down, 0,    // lower ghost row comes from below
                     MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Sendrecv(&u_old[idx(0, 1)],       n, MPI_DOUBLE, down, 1,    // my bottom row goes down
                     &u_old[idx(0, cnt + 1)], n, MPI_DOUBLE, up,   1,    // upper ghost row comes from above
                     MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        t_comm += MPI_Wtime() - tc;

        // Same update as the serial solver, on this rank's own rows only.
        for (int l = 1; l <= cnt; ++l)
            for (int i = 1; i < N; ++i)
                u_new[idx(i, l)] = (1.0 - 4.0 * r) * u_old[idx(i, l)]
                                 + r * (u_old[idx(i + 1, l)] + u_old[idx(i - 1, l)]
                                      + u_old[idx(i, l + 1)] + u_old[idx(i, l - 1)]);
        std::swap(u_old, u_new);
    }
    const double t_total = MPI_Wtime() - t0;
    const double t_comp = t_total - t_comm;

    // Report the maximum over ranks.
    double mine[3] = {t_total, t_comp, t_comm}, worst[3];
    MPI_Reduce(mine, worst, 3, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    // Rows this rank reports: its own rows, plus the plate edge on the first and last rank.
    const int lo = (rank == 0) ? 0 : 1;
    const int hi = cnt + ((rank == P - 1) ? 1 : 0);

    // ---- Error against the exact solution (test V only) ----
    double my_inf = 0.0, my_sum = 0.0, err_inf = 0.0, err_sum = 0.0;
    if (c.kase == "V") {
        const double decay = std::exp(-2.0 * pi * pi * T);
        for (int l = lo; l <= hi; ++l)
            for (int i = 0; i <= N; ++i) {
                const double exact = std::sin(pi * i * h) * std::sin(pi * (j0 - 1 + l) * h) * decay;
                const double e = std::fabs(u_old[idx(i, l)] - exact);
                if (e > my_inf) my_inf = e;
                my_sum += e * e;
            }
    }
    MPI_Reduce(&my_inf, &err_inf, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&my_sum, &err_sum, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        std::printf("decomp=%s P=%d N=%d r=%g steps=%d T=%g t_total=%.6f t_comp=%.6f t_comm=%.6f",
                    c.decomp.c_str(), P, N, r, steps, T, worst[0], worst[1], worst[2]);
        if (c.kase == "V") std::printf(" err_inf=%.6e err_2=%.6e", err_inf, std::sqrt(h * h * err_sum));
        std::printf("\n");
    }

    // ---- Output: gather every strip on rank 0 and write the same file as the serial solver ----
    int rc = 0;
    if (!c.out.empty()) {
        std::vector<int> counts(P), displs(P);
        for (int p = 0; p < P; ++p) {
            const int rows  = rows_of(p) + (p == 0 ? 1 : 0) + (p == P - 1 ? 1 : 0);
            const int first = (p == 0) ? 0 : first_of(p);
            counts[p] = rows * n;        // how many numbers rank p sends
            displs[p] = first * n;       // where they go in the full grid
        }
        std::vector<double> full;
        if (rank == 0) full.resize((std::size_t)n * n);
        MPI_Gatherv(&u_old[idx(0, lo)], (hi - lo + 1) * n, MPI_DOUBLE,
                    full.data(), counts.data(), displs.data(), MPI_DOUBLE, 0, MPI_COMM_WORLD);
        if (rank == 0) {
            std::FILE* f = std::fopen(c.out.c_str(), "wb");
            if (!f || std::fwrite(full.data(), sizeof(double), full.size(), f) != full.size()) {
                std::fprintf(stderr, "error: cannot write %s\n", c.out.c_str());
                rc = 1;
            }
            if (f) std::fclose(f);
        }
    }

    MPI_Finalize();
    return rc;
}
