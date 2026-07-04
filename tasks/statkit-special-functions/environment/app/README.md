# statkit

A small, dependency-free C11 toolkit for classical hypothesis testing. It
provides numerically stable special functions (regularized incomplete gamma and
beta), the chi-square / Student-t / F cumulative distribution functions built on
top of them, and a `statctl` command-line driver that runs goodness-of-fit and
two-sample t-tests from a simple `.spec` file.

## Build

    make            # build build/libstatkit.a and build/statctl
    make test       # build and run the acceptance suite in tests/
    make clean

Only a C compiler and libm are required.

## Layout

See `docs/architecture.md`. The public API is in `include/statkit/`; the math is
specified in `docs/ALGORITHMS.md`; the `statctl` input and report formats are in
`docs/FORMAT.md`.

## Usage

    build/statctl data/fixtures/mixed_suite.spec -o report.json
