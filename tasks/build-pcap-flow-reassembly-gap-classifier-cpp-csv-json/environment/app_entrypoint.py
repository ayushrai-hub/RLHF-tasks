import subprocess
import sys


def main() -> int:
    subprocess.run(["/app/scripts/build.sh"], check=True)
    return subprocess.call([
        "/app/bin/flowgap",
        "--csv",
        "/app/input/packets.csv",
        "--out",
        "/app/output.json",
    ])


if __name__ == "__main__":
    sys.exit(main())
