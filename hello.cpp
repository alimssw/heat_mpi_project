// hello.cpp: each MPI rank prints its rank, the total number of ranks and the host it runs on.
#include <mpi.h>
#include <cstdio>

int main(int argc, char** argv)
{
    MPI_Init(&argc, &argv);

    int rank, size, len;
    char host[MPI_MAX_PROCESSOR_NAME];
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    MPI_Get_processor_name(host, &len);

    std::printf("rank %d of %d on %s\n", rank, size, host);

    MPI_Finalize();
    return 0;
}
