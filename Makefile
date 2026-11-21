# Build with: make        Clean with: make clean
.RECIPEPREFIX = >
CXX      = mpicxx
CXXFLAGS = -std=c++17 -O2 -ffp-contract=off -Wall -Wextra -DOMPI_SKIP_MPICXX

all: hello pingpong

hello: hello.cpp
> $(CXX) $(CXXFLAGS) -o $@ $<

pingpong: pingpong.cpp
> $(CXX) $(CXXFLAGS) -o $@ $<

clean:
> rm -f hello pingpong
