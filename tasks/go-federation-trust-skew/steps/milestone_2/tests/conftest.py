import subprocess
from pathlib import Path

GRADE_SRC = Path("/tests/grade/m4_grade_test.go")
TARGET = Path("/app/environment/internal/ward/m4_grade_test.go")


def pytest_configure(config):
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cp", str(GRADE_SRC), str(TARGET)], check=True)
