// pingpong.cpp: measures the one-way time of a message of m bytes between rank 0 and rank 1.
// Rank 0 sends m bytes to rank 1, which sends them straight back. The round trip is
// averaged over many repetitions and halved. Output is CSV: bytes,one_way_seconds,reps.
// Run it with exactly 2 processes. Where they run (same VM or two VMs) is chosen with mpirun.
#include <mpi.h>
#include <algorithm>
#include <cstdio>
#include <vector>

static const int    WARMUP     = 5;
static const double TARGET_SEC = 0.5;   // aim for about this much time per message size
static const int    MIN_REPS   = 5;
static const int    MAX_REPS   = 2000;

// one round trip of m bytes; rank 0 starts, rank 1 echoes
static void round_trip(int rank, std::vector<char>& buf, int m)
{
    if (rank == 0) {
        MPI_Send(buf.data(), m, MPI_BYTE, 1, 0, MPI_COMM_WORLD);
        MPI_Recv(buf.data(), m, MPI_BYTE, 1, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    } else {
        MPI_Recv(buf.data(), m, MPI_BYTE, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Send(buf.data(), m, MPI_BYTE, 0, 0, MPI_COMM_WORLD);
    }
}

int main(int argc, char** argv)
{
    MPI_Init(&argc, &argv);

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    if (size != 2) {
        if (rank == 0) std::fprintf(stderr, "pingpong needs exactly 2 processes (got %d)\n", size);
        MPI_Finalize();
        return 1;
    }

    char host[MPI_MAX_PROCESSOR_NAME];
    int len;
    MPI_Get_processor_name(host, &len);
    // print each rank's host so the output records where the two processes ran
    std::fprintf(stderr, "# rank %d on %s\n", rank, host);

    const int max_bytes = 16 * 1024 * 1024;
    std::vector<char> buf(max_bytes, 1);

    if (rank == 0) std::printf("bytes,one_way_seconds,reps\n");

    for (int m = 8; m <= max_bytes; m *= 2) {
        for (int i = 0; i < WARMUP; ++i) round_trip(rank, buf, m);

        // estimate the round trip time to choose the number of repetitions
        MPI_Barrier(MPI_COMM_WORLD);
        double t0 = MPI_Wtime();
        round_trip(rank, buf, m);
        double est = MPI_Wtime() - t0;

        int reps = 0;
        if (rank == 0) {
            reps = (est > 0.0) ? (int)(TARGET_SEC / est) : MAX_REPS;
            reps = std::max(MIN_REPS, std::min(MAX_REPS, reps));
        }
        MPI_Bcast(&reps, 1, MPI_INT, 0, MPI_COMM_WORLD);

        MPI_Barrier(MPI_COMM_WORLD);
        t0 = MPI_Wtime();
        for (int i = 0; i < reps; ++i) round_trip(rank, buf, m);
        double t1 = MPI_Wtime();

        if (rank == 0) {
            double one_way = (t1 - t0) / reps / 2.0;
            std::printf("%d,%.9e,%d\n", m, one_way, reps);
            std::fflush(stdout);
        }
    }

    MPI_Finalize();
    return 0;
}
