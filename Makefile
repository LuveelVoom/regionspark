# OpenMP build. Apple clang has no OpenMP: on macOS this picks Homebrew g++-N if installed
# (brew install gcc); otherwise `make nomp` builds a single-threaded binary with any C++17 compiler.
CXX ?= g++
ifeq ($(shell uname),Darwin)
  BREWGXX := $(lastword $(sort $(wildcard /opt/homebrew/bin/g++-[0-9]* /usr/local/bin/g++-[0-9]*)))
  ifneq ($(BREWGXX),)
    CXX := $(BREWGXX)
  endif
endif
CXXFLAGS ?= -O2 -std=c++17 -Wall

regionspark: regionspark.cpp
	$(CXX) $(CXXFLAGS) -fopenmp -o $@ $<

nomp:
	$(CXX) $(CXXFLAGS) -o regionspark regionspark.cpp

test: regionspark
	python3 tests/test_rule.py
	sh tests/run_cases.sh stop

.PHONY: nomp test
