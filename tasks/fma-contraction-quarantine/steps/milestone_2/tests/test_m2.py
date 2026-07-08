"""Milestone 2: certify HAZARD vs BENIGN with a witness for every HAZARD."""

import gradelib as G


RESULT = "/app/output/result_2.json"


class TestMilestone2:
    """Hazard partition, witnesses, and invariant ids for milestone 2."""

    def test_result_is_object(self):
        """result_2.json exists and is a JSON object."""
        data = G.load_result(RESULT)
        assert isinstance(data, dict), "result_2.json must be a JSON object"

    def test_all_kernels_present(self):
        """Every kernel carries a HAZARD or BENIGN verdict."""
        data = G.load_result(RESULT)
        for k in G.KERNELS:
            assert k in data, "missing kernel entry: %s" % k
            v = data[k].get("verdict")
            assert v in ("HAZARD", "BENIGN"), "%s verdict must be HAZARD or BENIGN" % k

    def test_partition_and_witnesses(self):
        """The partition matches ground truth and every HAZARD witness checks out."""
        data = G.load_result(RESULT)
        sb = G.build("strict")
        rb = G.build("release")
        for kernel in G.KERNELS:
            truth, _ = G.truth_is_hazard(kernel, sb, rb)
            verdict = data[kernel]["verdict"]
            if truth:
                assert verdict == "HAZARD", (
                    "%s breaches its invariant under release but was marked BENIGN"
                    % kernel
                )
                inv = data[kernel].get("invariant")
                assert inv == G.KERNELS[kernel][2], "%s invariant id must be %s" % (
                    kernel,
                    G.KERNELS[kernel][2],
                )
                witness = data[kernel].get("witness")
                assert isinstance(witness, list) and witness, (
                    "%s HAZARD needs a witness list" % kernel
                )
                so = G.run(sb, kernel, witness)
                ro = G.run(rb, kernel, witness)
                assert G.inv_holds(kernel, witness, so), (
                    "%s witness must satisfy the invariant under the strict build"
                    % kernel
                )
                assert not G.inv_holds(kernel, witness, ro), (
                    "%s witness must violate the invariant under the release build"
                    % kernel
                )
            else:
                assert verdict == "BENIGN", (
                    "%s stays within contract under release but was flagged HAZARD"
                    % kernel
                )
