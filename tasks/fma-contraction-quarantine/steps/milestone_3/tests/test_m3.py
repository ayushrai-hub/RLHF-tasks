"""Milestone 3: the minimal per-translation-unit flag-suppression manifest."""

import copy

import gradelib as G


RESULT = "/app/output/result_3.json"


def _manifest():
    data = G.load_result(RESULT)
    assert isinstance(data, dict), "result_3.json must be a JSON object"
    norm = {}
    valid_tu = set(G.TUS) | {t + ".c" for t in G.TUS}
    for tu, toks in data.items():
        assert tu in valid_tu, "unknown translation unit: %s" % tu
        assert isinstance(toks, list) and toks, (
            "%s must map to a non-empty flag list" % tu
        )
        for t in toks:
            assert t in G.SUPPRESS_TOKENS, "unknown flag token: %s" % t
        norm[tu] = list(toks)
    return norm


HAZARDS = ["cross2", "recover", "cascade", "polarity", "domain_guard"]


def _all_invariants_hold(binp):
    for kernel in G.KERNELS:
        for args in G.HELDOUT[kernel]:
            out = G.run(binp, kernel, args)
            if not G.inv_holds(kernel, args, out):
                return False, (kernel, args)
    return True, None


class TestMilestone3:
    """Sufficiency and minimality of the suppression manifest."""

    def test_sufficiency(self):
        """Under the manifest every kernel holds its invariant on held-out inputs."""
        manifest = _manifest()
        binp = G.build(manifest)
        ok, where = _all_invariants_hold(binp)
        assert ok, "manifest is insufficient: %s still breaches its invariant" % (
            where,
        )

    def test_held_out_consistency(self):
        """A manifest lucky on one input is not enough: each hazard's invariant
        must hold across several independent held-out inputs, not the shipped
        samples that trigger nothing."""
        manifest = _manifest()
        binp = G.build(manifest)
        for kernel in HAZARDS:
            inputs = G.HELDOUT[kernel]
            for trial in range(4):
                args = inputs[trial % len(inputs)]
                out = G.run(binp, kernel, args)
                assert G.inv_holds(kernel, args, out), (
                    "%s held-out trial %d (%s) breaches under the manifest"
                    % (kernel, trial, args)
                )

    def test_minimality(self):
        """Re-adding any suppressed flag must re-break some invariant."""
        manifest = _manifest()
        for tu in list(manifest):
            for tok in list(manifest[tu]):
                reduced = copy.deepcopy(manifest)
                reduced[tu].remove(tok)
                if not reduced[tu]:
                    del reduced[tu]
                binp = G.build(reduced)
                ok, _ = _all_invariants_hold(binp)
                assert not ok, (
                    "re-adding %s on %s breaks nothing; that suppression is unnecessary"
                    % (tok, tu)
                )
