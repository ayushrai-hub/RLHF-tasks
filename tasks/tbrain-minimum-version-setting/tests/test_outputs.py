import os
import re
import subprocess
import textwrap
from pathlib import Path


APP = Path("/app")
BIN = APP / "target" / "debug" / "just"


def build_binary():
    result = subprocess.run(
        ["cargo", "build", "--locked", "--offline", "--bin", "just"],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert BIN.exists(), "expected the just binary to be built"


def write_justfile(path, body):
    path.write_text(textwrap.dedent(body).strip() + "\n")


def run_just(workdir, *args):
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    return subprocess.run(
        [str(BIN), "--justfile", str(Path(workdir) / "justfile"), *args],
        cwd=workdir,
        text=True,
        capture_output=True,
        timeout=30,
        env=env,
    )


def current_version():
    result = subprocess.run([str(BIN), "--version"], cwd=APP, text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
    assert match, result.stdout
    return match.group(1)


def test_satisfied_and_equal_requirements_run_recipes(tmp_path):
    """A low or exactly equal minimum version permits normal recipe execution."""
    build_binary()
    version = current_version()
    write_justfile(
        tmp_path / "justfile",
        f"""
        set minimum-version := "0.0.1"

        default:
          @echo low-ok

        equal:
          @echo equal-{version}
        """,
    )

    low = run_just(tmp_path)
    assert low.returncode == 0, low.stderr
    assert low.stdout == "low-ok\n"

    write_justfile(
        tmp_path / "justfile",
        f"""
        set minimum-version := "{version}"

        equal:
          @echo exact-ok
        """,
    )
    equal = run_just(tmp_path, "equal")
    assert equal.returncode == 0, equal.stderr
    assert equal.stdout == "exact-ok\n"


def test_future_requirement_fails_before_recipe_side_effects(tmp_path):
    """A newer required version stops before any recipe command can run."""
    build_binary()
    marker = tmp_path / "ran.txt"
    write_justfile(
        tmp_path / "justfile",
        f"""
        set minimum-version := "999.1.2"

        default:
          @printf ran > {marker}
        """,
    )

    result = run_just(tmp_path)
    assert result.returncode != 0
    assert "requires just 999.1.2 or later" in result.stderr
    assert current_version() in result.stderr
    assert "minimum-version" in result.stderr
    assert not marker.exists()


def test_invalid_and_non_literal_values_are_rejected(tmp_path):
    """The setting accepts only plain semantic-version string literals."""
    build_binary()
    cases = [
        ('set minimum-version := "one.two.three"', "invalid version `one.two.three`"),
        ('set minimum-version := ("1." + "2.3")', "must be a plain string literal"),
        ("set minimum-version := x'1.2.3'", "must be a plain string literal"),
        ("set minimum-version := '''1.2.3'''", "must be a plain string literal"),
    ]

    for index, (line, expected) in enumerate(cases):
        case_dir = tmp_path / f"case_{index}"
        case_dir.mkdir()
        write_justfile(
            case_dir / "justfile",
            f"""
            {line}

            default:
              @echo should-not-run
            """,
        )
        result = run_just(case_dir)
        assert result.returncode != 0
        assert expected in result.stderr
        assert "should-not-run" not in result.stdout


def test_dump_and_other_settings_remain_compatible(tmp_path):
    """Existing settings and dump output still parse around the new setting."""
    build_binary()
    write_justfile(
        tmp_path / "justfile",
        """
        set dotenv-load := false
        set minimum-version := "0.0.1"
        set shell := ["sh", "-cu"]

        greet name:
          @echo hello {{name}}
        """,
    )

    dumped = run_just(tmp_path, "--dump")
    assert dumped.returncode == 0, dumped.stderr
    assert 'set minimum-version := "0.0.1"' in dumped.stdout
    assert 'set shell := ["sh", "-cu"]' in dumped.stdout

    run = run_just(tmp_path, "greet", "Ada")
    assert run.returncode == 0, run.stderr
    assert run.stdout == "hello Ada\n"
