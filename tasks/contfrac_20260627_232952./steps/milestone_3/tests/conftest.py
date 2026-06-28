import subprocess
from pathlib import Path

CASES = Path(__file__).parent / "cases"


def pytest_configure(config):
    src = Path("/app/contfrac.cpp")
    if src.exists():
        subprocess.run(["g++","-O2","-std=c++17","-o","/app/contfrac","/app/contfrac.cpp"],cwd="/app",check=False)


def run_case(name):
    inp = (CASES / "in" / f"{name}.txt").read_text()
    if not Path("/app/contfrac").exists():
        return "<not built>"
    p = subprocess.run(["/app/contfrac"], input=inp, capture_output=True, text=True)
    return p.stdout


def check(name):
    expected = (CASES / "exp" / f"{name}.txt").read_text()
    actual = run_case(name)
    assert actual == expected, f"{name} mismatch\n--- expected ---\n{expected}\n--- actual ---\n{actual}\n"
