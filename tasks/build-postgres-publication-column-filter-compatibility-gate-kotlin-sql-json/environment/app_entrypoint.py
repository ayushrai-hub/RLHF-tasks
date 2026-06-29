#!/usr/bin/env python3
import os
import subprocess
import sys

CP = "/app/build/pubgate.jar:/usr/share/java/gson.jar:/usr/share/java/sqlite-jdbc.jar:/usr/share/java/kotlin-stdlib.jar:/usr/share/java/kotlin-stdlib-jdk7.jar:/usr/share/java/kotlin-stdlib-jdk8.jar"
MAIN = "com.terminus.pubgate.MainKt"


def main() -> int:
    if not os.path.exists("/app/build/pubgate.jar"):
        subprocess.run(["/app/build.sh"], cwd="/app", check=True)
    return subprocess.run(["java", "-cp", CP, MAIN, *sys.argv[1:]], cwd="/app").returncode


if __name__ == "__main__":
    raise SystemExit(main())
