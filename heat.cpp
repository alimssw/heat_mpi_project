#include <chrono>
#include <cmath>
#include <cstdio>
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
    std::string decomp = "serial";
    bool allow_unstable = false;   // Task 6.7 only: run above the stability limit on purpose
};

int main(int argc, char** argv) {
    Config c;
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
        else { std::fprintf(stderr, "error: unknown option %s\n", key.c_str()); return 1; }
    }
    if (c.r <= 0.0 || (c.r > 0.25 && !c.allow_unstable)) {
        std::fprintf(stderr,
            "error: r=%g is unstable. The explicit scheme needs 0 < r <= 0.25.\n", c.r);
        return 1;
    }
    if (c.decomp != "serial") {
        std::fprintf(stderr, "error: --decomp %s is not implemented yet, only serial\n", c.decomp.c_str());
        return 1;
    }
    if (c.steps < 0 && c.T < 0.0) {
        std::fprintf(stderr, "error: give --steps or --T\n");
        return 1;
    }

    // Grid
    const int N = c.N;
    const int n = N + 1;                 // nodes per direction, boundary included
    const double h = 1.0 / N;            // grid spacing
    auto idx = [n](int i, int j) { return j * n + i; };  // row j is y = j*h; i varies fastest

    std::vector<double> u_old(n * n, 0.0), u_new(n * n, 0.0);

    // Initial and boundary values. Interior starts at 0 for Cases 1 and 2.
    const double pi = std::acos(-1.0);
    if (c.kase == "V") {
        for (int j = 1; j < N; ++j)
            for (int i = 1; i < N; ++i)
                u_old[idx(i, j)] = std::sin(pi * i * h) * std::sin(pi * j * h);
    } else if (c.kase == "1" || c.kase == "2") {
        for (int i = 0; i <= N; ++i)              // bottom (y=0) and top (y=1) edges, corners included
            u_old[idx(i, 0)] = u_old[idx(i, N)] = 1.0;
        if (c.kase == "1")
            for (int j = 0; j <= N; ++j)          // left and right edges too
                u_old[idx(0, j)] = u_old[idx(N, j)] = 1.0;
        u_new = u_old;                            // edge values must be in both arrays
    } else {
        std::fprintf(stderr, "error: --case must be 1, 2 or V\n");
        return 1;
    }

    // Time step. alpha = 1, so dt = r * h^2.
    int steps = c.steps;
    double r = c.r;
    if (c.T > 0.0) {   // --T given: choose steps so T/dt is a whole number and r is not exceeded
        steps = (int)std::ceil(c.T / (c.r * h * h));
        r = c.T / steps / (h * h);
    }
    const double dt = r * h * h;
    const double T = steps * dt;

    // Time loop (only this part is timed)
    auto t0 = std::chrono::steady_clock::now();
    for (int s = 0; s < steps; ++s) {
        for (int j = 1; j < N; ++j)
            for (int i = 1; i < N; ++i)
                u_new[idx(i, j)] = (1.0 - 4.0 * r) * u_old[idx(i, j)]
                                 + r * (u_old[idx(i + 1, j)] + u_old[idx(i - 1, j)]
                                      + u_old[idx(i, j + 1)] + u_old[idx(i, j - 1)]);
        std::swap(u_old, u_new);
    }
    auto t1 = std::chrono::steady_clock::now();
    const double t_total = std::chrono::duration<double>(t1 - t0).count();

    // Error against the exact solution (test V only)
    double err_inf = 0.0, err_sum = 0.0;
    if (c.kase == "V") {
        const double decay = std::exp(-2.0 * pi * pi * T);
        for (int j = 0; j <= N; ++j)
            for (int i = 0; i <= N; ++i) {
                const double exact = std::sin(pi * i * h) * std::sin(pi * j * h) * decay;
                const double e = std::fabs(u_old[idx(i, j)] - exact);
                if (e > err_inf) err_inf = e;
                err_sum += e * e;
            }
    }
    const double err_2 = std::sqrt(h * h * err_sum);

    // One summary line in key=value form
    std::printf("decomp=%s P=1 N=%d r=%g steps=%d T=%g t_total=%.6f t_comp=%.6f t_comm=0",
                c.decomp.c_str(), N, r, steps, T, t_total, t_total);
    if (c.kase == "V") std::printf(" err_inf=%.6e err_2=%.6e", err_inf, err_2);
    std::printf("\n");

    // Full (N+1) x (N+1) field as raw doubles, row by row, no header
    if (!c.out.empty()) {
        std::FILE* f = std::fopen(c.out.c_str(), "wb");
        if (!f) { std::fprintf(stderr, "error: cannot open %s\n", c.out.c_str()); return 1; }
        std::fwrite(u_old.data(), sizeof(double), u_old.size(), f);
        std::fclose(f);
    }
    return 0;
}
