#include <cmath>
#include <vector>
#include <cstdio>
#include <string>

struct Config {
    std::string kase = "V";        // "1", "2" or "V"
    int N = 64;                    // intervals per direction
    double r = 0.2;                // alpha*dt/h^2
    int steps = -1;                // -1 means not given
    double T = -1.0;               // -1 means not given
    std::string out;               // empty means no output file
    std::string decomp = "serial";
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
        else { std::fprintf(stderr, "error: unknown option %s\n", key.c_str()); return 1; }
    }
    if (c.r <= 0.0 || c.r > 0.25) {
        std::fprintf(stderr,
            "error: r=%g is unstable. The explicit scheme needs 0 < r <= 0.25.\n", c.r);
        return 1;
    }
    if (c.steps < 0 && c.T < 0.0) {
        std::fprintf(stderr, "error: give --steps or --T\n");
        return 1;
    }
    std::printf("case=%s N=%d r=%g steps=%d T=%g decomp=%s\n",
                c.kase.c_str(), c.N, c.r, c.steps, c.T, c.decomp.c_str());

    const int N = c.N;
    const int n = N + 1;                 // nodes per direction, boundary included
    const double h = 1.0 / N;            // grid spacing
    auto idx = [n](int i, int j) { return j * n + i; };  // row j is y = j*h; i varies fastest

    std::vector<double> u_old(n * n, 0.0), u_new(n * n, 0.0);

    // Test V initial condition: sin(pi x) sin(pi y) inside, 0 on all four edges
    const double pi = std::acos(-1.0);
    for (int j = 1; j < N; ++j)
        for (int i = 1; i < N; ++i)
            u_old[idx(i, j)] = std::sin(pi * i * h) * std::sin(pi * j * h);

    // temporary check, delete later
    std::printf("centre=%.6f quarter=%.6f corner=%.6f\n",
                u_old[idx(N / 2, N / 2)], u_old[idx(N / 4, N / 2)], u_old[idx(0, 0)]);
    return 0;
}
