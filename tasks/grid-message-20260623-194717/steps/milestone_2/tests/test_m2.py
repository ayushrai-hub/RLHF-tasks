import subprocess
import os


class TestMilestone2:
    def test_fsk_decoder(self):
        """This tests that the fsk decoder correctly decodes and prints the message"""
        test_runner_c = "/tests/test_m2_runner.c"
        src_c = "/app/fsk_decoder.c"

        assert os.path.exists(test_runner_c), f"{test_runner_c} not found!"
        assert os.path.exists(src_c), f"{src_c} not found!"

        # Defensive compilation
        compile_res = subprocess.run(
            [
                "gcc",
                "-o",
                "/tmp/test_m2",
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

        run_res = subprocess.run(["/tmp/test_m2"], capture_output=True, text=True)

        # STRICT VALIDATION: The output must be exactly "PASS" (with no trailing garbage)
        actual_output = run_res.stdout.strip()
        assert actual_output == "PASS", (
            f"Output mismatch. Expected exactly 'PASS', got: '{actual_output}'"
        )
        assert run_res.returncode == 0
