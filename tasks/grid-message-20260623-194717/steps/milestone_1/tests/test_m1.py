import subprocess
import os


class TestMilestone1:
    def test_pll_tracking(self):
        """ This tests that the loop will lock at various frequencies """
        test_runner_c = "/tests/test_m1_runner.c"
        src_c = "/app/grid_pll.c"

        assert os.path.exists(test_runner_c), f"{test_runner_c} not found!"
        assert os.path.exists(src_c), f"{src_c} not found!"

        # Defensive compilation
        compile_res = subprocess.run(
            [
                "gcc",
                "-o",
                "/tmp/test_m1",
                test_runner_c,
                src_c,
                "-I/app",
                "-I/app/headers",
                "-I/environment/headers",
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        assert compile_res.returncode == 0, f"Compilation Failed:\n{compile_res.stderr}"

        # Run the strict multi-frequency test
        run_res = subprocess.run(["/tmp/test_m1"], capture_output=True, text=True)
        print("\n--- C EXECUTABLE OUTPUT ---")
        print(run_res.stdout)
        print("---------------------------\n")

        assert run_res.returncode == 0, (
            f"PLL Tracking Failed. Output:\n{run_res.stdout}"
        )
        assert "ALL PLL TESTS PASSED" in run_res.stdout, (
            "Did not pass all frequency extremes."
        )
