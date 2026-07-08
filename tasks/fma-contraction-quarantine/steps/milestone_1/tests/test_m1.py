"""Milestone 1: per-kernel divergence between the strict and release builds."""

import gradelib as G


RESULT = "/app/output/result_1.json"


class TestMilestone1:
    """Divergence partition and witnesses for milestone 1."""

    def test_result_is_object(self):
        """result_1.json exists and is a JSON object."""
        data = G.load_result(RESULT)
        assert isinstance(data, dict), "result_1.json must be a JSON object"

    def test_all_kernels_present(self):
        """Every kernel has a boolean diverges field."""
        data = G.load_result(RESULT)
        for k in G.KERNELS:
            assert k in data, "missing kernel entry: %s" % k
            assert "diverges" in data[k], "missing 'diverges' for %s" % k
            assert isinstance(data[k]["diverges"], bool), (
                "'diverges' must be bool for %s" % k
            )

    def test_divergence_claims_correct(self):
        """Each claimed divergence reproduces; each non-divergence survives the sweep."""
        data = G.load_result(RESULT)
        sb = G.build("strict")
        rb = G.build("release")
        for kernel in G.KERNELS:
            entry = data[kernel]
            if entry["diverges"]:
                witness = entry.get("witness")
                assert isinstance(witness, list) and witness, (
                    "%s marked diverging needs a witness list" % kernel
                )
                so = G.run(sb, kernel, witness)
                ro = G.run(rb, kernel, witness)
                assert not G.same_bits(so, ro), (
                    "%s witness %s does not diverge (strict==release)"
                    % (kernel, witness)
                )
            else:
                div, args = G.any_divergence(kernel, sb, rb)
                assert not div, "%s marked non-diverging but input %s diverges" % (
                    kernel,
                    args,
                )
