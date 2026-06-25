import subprocess
import os
import shutil
import random
import re

WORD_BANK = [
    "ZEPHYR",
    "ORACLE",
    "signal",
    "System",
    "frequency",
    "FILTER",
    "widget",
    "ROUTER",
    "Silicon",
    "kernel",
]

class TestMilestone3:
    def test_full_integration(self):
        """This checks that the main.c program correctly decodes a message and prints the number of frames processed"""
        # 1. Inject the Secure Hardware Mock
        shutil.copy("/tests/mock_adc.c", "/app/mock_adc.c")
        # 2. Synchronize the Word Bank via CFLAGS
        random.seed(42)
        expected_word = random.choice(WORD_BANK)
        cflags = f"-DTEST_SECRET_WORD={expected_word}"

        # 3. Build Zephyr (Using "-p always" to clear stale CMake caches from previous agents)
        build_res = subprocess.run(
            [
                "west",
                "build",
                "-p",
                "always",
                "-b",
                "native_sim/native/64",
                "/app",
                "--",
                f"-DEXTRA_CFLAGS={cflags}",
            ],
            capture_output=True,
            text=True,
            timeout=300
        )
        assert build_res.returncode == 0, (
            f"Zephyr Build Failed:\n{build_res.stderr}\n{build_res.stdout}"
        )

        # 4. Run the RTOS Simulator
        run_res = subprocess.run(
            ["/app/build/zephyr/zephyr.exe"], capture_output=True, text=True, timeout=300
        )
        output = run_res.stdout.strip()

        # 5. Strict Validation
        assert run_res.returncode == 0, "Zephyr App Crashed"

        # Anti-Cheating check
        assert "[MOCK_ENV] SECRET_WORD" not in output, (
            "FATAL: Mock environment leaked the secret word!"
        )

        # Verify decoding
        expected_output = f"DECODED: {expected_word}"
        assert expected_output in output, (
            f"Failed to decode message.\n"
            f"Expected: {expected_output}\n"
            f"Output log: \n{output}"
        )

        # 6. Verify Early Exit (QA Reviewer Fix)
        frames_match = re.search(r"FRAMES_PROCESSED:\s*(\d+)", output)
        assert frames_match, "FAIL: Did not find 'FRAMES_PROCESSED: [count]' in output."
        frames_processed = int(frames_match.group(1))
        
        # Calculate exactly when the agent should have broken out based on word length
        # Preamble (max 240) + Characters (10 bits each * max 62 frames per bit)
        # We add 200 frames of padding just to be safe with rounding/moving averages
        max_expected_frames = 240 + ((len(expected_word) + 1) * 620) + 200
        
        assert frames_processed <= max_expected_frames, (
            f"FAIL: Agent did not break out immediately after the null terminator. "
            f"Expected <= {max_expected_frames} frames for '{expected_word}', "
            f"but processed {frames_processed}."
        )
        
    def test_no_message_format(self):
        """This checks that when no message is sent that the proper output string is printed"""
        # The QA report identified that the "NO message found" negative path was never tested.
        # This builds the app without a target word to ensure it fails gracefully per instructions.
        
        # QA Fix: Inject the mock independently so this test isn't order-dependent
        shutil.copy("/tests/mock_adc.c", "/app/mock_adc.c")

        build_res = subprocess.run(
            ["west", "build", "-p", "always", "-b", "native_sim/native/64", "/app"],
            capture_output=True,
            text=True,
        )
        assert build_res.returncode == 0, "Zephyr Build Failed on empty scenario."

        # Pass an environment variable to our secure mock to disable FSK transmission
        env = os.environ.copy()
        env["SCENARIO"] = "empty"

        run_res = subprocess.run(
            ["/app/build/zephyr/zephyr.exe"], capture_output=True, text=True, env=env
        )

        # Check for EXACT string formatting required by the instruction
        assert "NO message found\n" in run_res.stdout, (
            "Agent failed to print the required missing message error format."
        )