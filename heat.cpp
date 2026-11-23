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
    std::string decomp = "serial"; // serial, strips or blocks
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
        if (P != 1) return fail("--decomp serial needs exactly 1 process; use strips or blocks with mpirun -np P");
    } else if (c.decomp != "strips" && c.decomp != "blocks") {
        return fail("--decomp must be serial, strips or blocks");
    }

    // ---- Global grid ----
    const int N = c.N;
    const int n = N + 1;                 // nodes per direction, boundary included
    const double h = 1.0 / N;
    const double pi = std::acos(-1.0);

    // ---- Process grid: Py blocks in y (direction 0), Px blocks in x (direction 1) ----
    int dims[2] = {0, 0};
    if (c.decomp == "blocks") MPI_Dims_create(P, 2, dims);   // MPI picks the most square grid
    else { dims[0] = P; dims[1] = 1; }                       // serial and strips: one block wide
    const int Py = dims[0], Px = dims[1];
    if (Py > N - 1 || Px > N - 1) return fail("more processes than interior rows or columns");

    int periods[2] = {0, 0};             // non-periodic: outside the plate there is no neighbour
    MPI_Comm cart;
    MPI_Cart_create(MPI_COMM_WORLD, 2, dims, periods, 0, &cart);
    int coords[2];
    MPI_Cart_coords(cart, rank, 2, coords);
    const int cy = coords[0], cx = coords[1];
    int down, up, left, right;           // MPI_PROC_NULL at the edges of the plate
    MPI_Cart_shift(cart, 0, 1, &down, &up);
    MPI_Cart_shift(cart, 1, 1, &left, &right);

    // ---- Split the N-1 interior rows among Py blocks and the N-1 interior columns among Px ----
    // The first (N-1) % parts blocks get one extra row or column.
    auto count_of = [N](int k, int parts) { return (N - 1) / parts + (k < (N - 1) % parts ? 1 : 0); };
    auto first_of = [N](int k, int parts) {
        const int base = (N - 1) / parts, rem = (N - 1) % parts;
        return 1 + k * base + (k < rem ? k : rem);
    };
    const int nyl = count_of(cy, Py), j0 = first_of(cy, Py);   // rows owned, first owned row
    const int nxl = count_of(cx, Px), i0 = first_of(cx, Px);   // columns owned, first owned column

    // Local storage: (nyl+2) rows by (nxl+2) columns, row by row.
    // Local (a, l) holds global node (i0 - 1 + a, j0 - 1 + l). The outer layer is ghost nodes,
    // or the fixed plate edge where the block touches it.
    const int w = nxl + 2;
    auto idx = [w](int a, int l) { return (std::size_t)l * w + a; };
    std::vector<double> u_old((std::size_t)(nyl + 2) * w), u_new;
    for (int l = 0; l <= nyl + 1; ++l)
        for (int a = 0; a <= nxl + 1; ++a)
            u_old[idx(a, l)] = initial_value(c.kase, i0 - 1 + a, j0 - 1 + l, N, h, pi);
    u_new = u_old;                       // edge values must be in both arrays

    // A column is not contiguous in memory: nyl values, one every w positions.
    MPI_Datatype column;
    MPI_Type_vector(nyl, 1, w, MPI_DOUBLE, &column);
    MPI_Type_commit(&column);

    // Rows are contiguous. Strips send the whole row of N+1 doubles (Part 2);
    // blocks send only the owned columns, so corner ghost values are never exchanged.
    const int ra = (Px == 1) ? 0 : 1;
    const int rw = (Px == 1) ? w : nxl;

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
    MPI_Barrier(cart);
    double t_comm = 0.0;
    const double t0 = MPI_Wtime();
    for (int s = 0; s < steps; ++s) {
        // Halo exchange. With MPI_PROC_NULL a call does nothing, so the plate edge stays fixed.
        const double tc = MPI_Wtime();
        MPI_Sendrecv(&u_old[idx(ra, nyl)],     rw, MPI_DOUBLE, up,   0,    // top row up
                     &u_old[idx(ra, 0)],       rw, MPI_DOUBLE, down, 0,    // lower ghost row from below
                     cart, MPI_STATUS_IGNORE);
        MPI_Sendrecv(&u_old[idx(ra, 1)],       rw, MPI_DOUBLE, down, 1,    // bottom row down
                     &u_old[idx(ra, nyl + 1)], rw, MPI_DOUBLE, up,   1,    // upper ghost row from above
                     cart, MPI_STATUS_IGNORE);
        MPI_Sendrecv(&u_old[idx(nxl, 1)],      1, column, right, 2,        // right column to the right
                     &u_old[idx(0, 1)],        1, column, left,  2,        // left ghost column from the left
                     cart, MPI_STATUS_IGNORE);
        MPI_Sendrecv(&u_old[idx(1, 1)],        1, column, left,  3,        // left column to the left
                     &u_old[idx(nxl + 1, 1)],  1, column, right, 3,        // right ghost column from the right
                     cart, MPI_STATUS_IGNORE);
        t_comm += MPI_Wtime() - tc;

        // Same update as the serial solver, on this block's own nodes only.
        for (int l = 1; l <= nyl; ++l)
            for (int a = 1; a <= nxl; ++a)
                u_new[idx(a, l)] = (1.0 - 4.0 * r) * u_old[idx(a, l)]
                                 + r * (u_old[idx(a + 1, l)] + u_old[idx(a - 1, l)]
                                      + u_old[idx(a, l + 1)] + u_old[idx(a, l - 1)]);
        std::swap(u_old, u_new);
    }
    const double t_total = MPI_Wtime() - t0;
    const double t_comp = t_total - t_comm;

    // Report the maximum over ranks.
    double mine[3] = {t_total, t_comp, t_comm}, worst[3];
    MPI_Reduce(mine, worst, 3, MPI_DOUBLE, MPI_MAX, 0, cart);

    // Rectangle a rank reports, in global indices: its own nodes plus any plate edge it touches.
    auto rect = [&](int p, int& gi, int& gj, int& ni, int& nj) {
        int pc[2];
        MPI_Cart_coords(cart, p, 2, pc);
        const int bot = (pc[0] == 0), top = (pc[0] == Py - 1), lft = (pc[1] == 0), rgt = (pc[1] == Px - 1);
        gj = first_of(pc[0], Py) - bot;  nj = count_of(pc[0], Py) + bot + top;
        gi = first_of(pc[1], Px) - lft;  ni = count_of(pc[1], Px) + lft + rgt;
    };
    int gi, gj, ni, nj;
    rect(rank, gi, gj, ni, nj);

    // ---- Error against the exact solution (test V only) ----
    double my_inf = 0.0, my_sum = 0.0, err_inf = 0.0, err_sum = 0.0;
    if (c.kase == "V") {
        const double decay = std::exp(-2.0 * pi * pi * T);
        for (int j = gj; j < gj + nj; ++j)
            for (int i = gi; i < gi + ni; ++i) {
                const double exact = std::sin(pi * i * h) * std::sin(pi * j * h) * decay;
                const double e = std::fabs(u_old[idx(i - i0 + 1, j - j0 + 1)] - exact);
                if (e > my_inf) my_inf = e;
                my_sum += e * e;
            }
    }
    MPI_Reduce(&my_inf, &err_inf, 1, MPI_DOUBLE, MPI_MAX, 0, cart);
    MPI_Reduce(&my_sum, &err_sum, 1, MPI_DOUBLE, MPI_SUM, 0, cart);

    if (rank == 0) {
        std::printf("decomp=%s P=%d Px=%d Py=%d N=%d r=%g steps=%d T=%g t_total=%.6f t_comp=%.6f t_comm=%.6f",
                    c.decomp.c_str(), P, Px, Py, N, r, steps, T, worst[0], worst[1], worst[2]);
        if (c.kase == "V") std::printf(" err_inf=%.6e err_2=%.6e", err_inf, std::sqrt(h * h * err_sum));
        std::printf("\n");
    }

    // ---- Output: every rank sends its rectangle to rank 0, which writes the serial file format ----
    int rc = 0;
    if (!c.out.empty()) {
        std::vector<double> buf((std::size_t)ni * nj);
        for (int j = 0; j < nj; ++j)
            for (int i = 0; i < ni; ++i)
                buf[(std::size_t)j * ni + i] = u_old[idx(gi + i - i0 + 1, gj + j - j0 + 1)];
        if (rank != 0) {
            MPI_Send(buf.data(), ni * nj, MPI_DOUBLE, 0, 9, cart);
        } else {
            std::vector<double> full((std::size_t)n * n);
            for (int p = 0; p < P; ++p) {
                int pi_, pj, pni, pnj;
                rect(p, pi_, pj, pni, pnj);
                if (p != 0) {
                    buf.resize((std::size_t)pni * pnj);
                    MPI_Recv(buf.data(), pni * pnj, MPI_DOUBLE, p, 9, cart, MPI_STATUS_IGNORE);
                }
                for (int j = 0; j < pnj; ++j)
                    for (int i = 0; i < pni; ++i)
                        full[(std::size_t)(pj + j) * n + (pi_ + i)] = buf[(std::size_t)j * pni + i];
            }
            std::FILE* f = std::fopen(c.out.c_str(), "wb");
            if (!f || std::fwrite(full.data(), sizeof(double), full.size(), f) != full.size()) {
                std::fprintf(stderr, "error: cannot write %s\n", c.out.c_str());
                rc = 1;
            }
            if (f) std::fclose(f);
        }
    }

    MPI_Type_free(&column);
    MPI_Comm_free(&cart);
    MPI_Finalize();
    return rc;
}
