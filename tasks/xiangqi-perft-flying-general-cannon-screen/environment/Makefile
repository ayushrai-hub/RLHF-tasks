CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17
SRCS := $(wildcard src/*.cpp)

perft: $(SRCS)
	$(CXX) $(CXXFLAGS) $(SRCS) -o perft

clean:
	rm -f perft
