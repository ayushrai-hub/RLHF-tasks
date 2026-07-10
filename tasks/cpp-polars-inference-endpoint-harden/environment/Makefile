CXX = g++
CXXFLAGS = -Wall -Wextra -O2 -std=c++17 -Iinclude -I/usr/include/jsoncpp
LDFLAGS = -ljsoncpp -lcrypto -lpthread

SRCS = src/main.cpp \
       src/ratified_policy.cpp \
       src/batch_gate.cpp \
       src/lock_guard.cpp \
       src/sidecar_exec.cpp \
       src/row_scorer.cpp \
       src/http_service.cpp

OBJS = $(SRCS:.cpp=.o)

all: score-server

score-server: $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $(OBJS) $(LDFLAGS)

install: score-server
	mkdir -p /app/bin
	cp score-server /app/bin/score-server

clean:
	rm -f score-server $(OBJS)

.PHONY: all install clean
