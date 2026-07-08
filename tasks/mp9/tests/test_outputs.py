"""Single-step tests for the gomvs tool. Every command fetches live from
https://proxy.golang.org; the pinned module versions are immutable published
artifacts, so their expected values are stable across runs.

Coverage: proxy version listing with Semantic Versioning ordering (including
+incompatible major versions), go.mod parsing of the current, quoted and block
dialects plus replace and exclude directives, the Minimal Version Selection
build list over shallow, shared-dependency and replace-bearing graphs, and
dependency resolution."""
import subprocess

import pytest

APP_DIR = "/app"
BINARY = "/app/gomvs"


@pytest.fixture(scope="module", autouse=True)
def build_binary():
    """Build the Go binary once before the tests in this module."""
    result = subprocess.run(
        ["go", "build", "-o", BINARY, "."],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"go build failed:\n{result.stderr}")


def run(args):
    """Run the gomvs binary and capture its result."""
    return subprocess.run([BINARY] + list(args), capture_output=True, text=True)


def lines_of(text):
    """Split captured stdout into non-empty stripped lines."""
    return [ln.strip() for ln in text.strip().splitlines() if ln.strip()]


def _semver_key(v):
    """Independent Go-module precedence key: numeric core, then a release above
    any pre-release, then pre-release fields with numerics below non-numerics.
    Build metadata (after '+', e.g. +incompatible) is dropped."""
    s = v.lstrip("v").split("+")[0]
    if "-" in s:
        core, pre = s.split("-", 1)
    else:
        core, pre = s, None
    maj, minr, pat = (int(x) for x in core.split("."))
    if pre is None:
        prekey = (1,)
    else:
        fields = []
        for f in pre.split("."):
            if f.isdigit():
                fields.append((0, int(f), ""))
            else:
                fields.append((1, 0, f))
        prekey = (0, tuple(fields))
    return (maj, minr, pat, prekey)


def test_sources_are_gofmt_clean():
    """Every Go source under the app is gofmt-formatted: gofmt -l lists nothing.
    The instructions require gofmt-clean code, so enforce it directly."""
    result = subprocess.run(
        ["gofmt", "-l", "."],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", f"gofmt -l flagged:\n{result.stdout}"


def test_go_vet_clean():
    """go vet reports no problems across the module. The instructions require
    go-vet-clean code, so enforce it directly."""
    result = subprocess.run(
        ["go", "vet", "./..."],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


class TestVersions:
    def test_sampler_versions_sorted(self):
        """versions returns sampler ascending in the tool's own semver order.
        Rather than pinning the full published list (which grows as new versions
        ship), assert the ordering property plus a stable subset of long-published
        versions in the expected relative order."""
        r = run(["versions", "rsc.io/sampler"])
        assert r.returncode == 0, r.stderr
        got = lines_of(r.stdout)
        # ordering property: each version is <= the next by the tool's sort.
        assert got == sorted(got, key=_semver_key), got
        # a stable subset of long-published versions appears, in order.
        known = ["v1.0.0", "v1.2.0", "v1.2.1", "v1.3.0", "v1.3.1"]
        for v in known:
            assert v in got, got
        idxs = [got.index(v) for v in known]
        assert idxs == sorted(idxs), got

    def test_quote_prerelease_ordering(self):
        """A pre-release sorts below the matching release: v1.5.3-pre1 last."""
        r = run(["versions", "rsc.io/quote"])
        assert r.returncode == 0, r.stderr
        got = lines_of(r.stdout)
        assert got == [
            "v0.9.9-pre1",
            "v1.0.0",
            "v1.1.0",
            "v1.2.0",
            "v1.2.1",
            "v1.3.0",
            "v1.4.0",
            "v1.5.0",
            "v1.5.1",
            "v1.5.2",
            "v1.5.3-pre1",
        ]
        assert got.index("v0.9.9-pre1") == 0
        assert got.index("v1.5.2") < got.index("v1.5.3-pre1")

    def test_uppercase_path_is_escaped(self):
        """A module path with uppercase letters resolves via proxy escaping."""
        r = run(["versions", "github.com/BurntSushi/toml"])
        assert r.returncode == 0, r.stderr
        got = lines_of(r.stdout)
        assert got[:3] == ["v0.1.0", "v0.2.0", "v0.3.0"]
        assert "v1.6.0" in got
        assert got == sorted(got, key=_semver_key)

    def test_incompatible_major_ordering(self):
        """A version list spanning v0..v3 with +incompatible majors sorts by
        numeric core, not lexically: v3.3.9 precedes v3.3.10, majors ascend."""
        r = run(["versions", "github.com/coreos/etcd"])
        assert r.returncode == 0, r.stderr
        got = lines_of(r.stdout)
        assert got[0] == "v0.1.0"
        assert got[-1] == "v3.3.27+incompatible"
        assert got == sorted(got, key=_semver_key)
        # numeric, not lexical: v3.3.9 must come before v3.3.10
        assert got.index("v3.3.9+incompatible") < got.index("v3.3.10+incompatible")
        # +incompatible major 2 ranks above major 0, below major 3
        assert got.index("v0.5.0-alpha.5") < got.index("v2.0.0-rc.1+incompatible")
        assert got.index("v2.0.0-rc.1+incompatible") < got.index("v3.3.27+incompatible")


class TestGoMod:
    def test_quote_gomod_quoted_dialect(self):
        """gomod parses the older quoted go.mod and reports no go directive."""
        r = run(["gomod", "rsc.io/quote", "v1.5.2"])
        assert r.returncode == 0, r.stderr
        assert lines_of(r.stdout) == [
            "module rsc.io/quote",
            "go none",
            "require rsc.io/sampler v1.3.0",
        ]

    def test_tools_gomod_block_and_go_directive(self):
        """gomod parses a require block and the go directive, sorted by path."""
        r = run(["gomod", "golang.org/x/tools", "v0.1.0"])
        assert r.returncode == 0, r.stderr
        assert lines_of(r.stdout) == [
            "module golang.org/x/tools",
            "go 1.12",
            "require github.com/yuin/goldmark v1.2.1",
            "require golang.org/x/mod v0.3.0",
            "require golang.org/x/net v0.0.0-20201021035429-f5854403a974",
            "require golang.org/x/sync v0.0.0-20201020160332-67f06af15bc9",
            "require golang.org/x/sys v0.0.0-20210119212857-b64e53b001e4",
            "require golang.org/x/xerrors v0.0.0-20200804184101-5ec99f83aff1",
        ]

    def test_incompatible_pseudo_require(self):
        """gomod echoes a require whose version carries both a pre-release and a
        +incompatible build tag, and escapes the uppercase Knetic path."""
        r = run(["gomod", "github.com/casbin/casbin", "v1.9.1"])
        assert r.returncode == 0, r.stderr
        assert lines_of(r.stdout) == [
            "module github.com/casbin/casbin",
            "go none",
            "require github.com/Knetic/govaluate "
            "v3.0.1-0.20171022003610-9aa49832a739+incompatible",
        ]

    def test_replace_and_exclude_directives(self):
        """gomod parses replace and exclude directives and prints them after the
        require lines, in the documented forms."""
        r = run(["gomod", "github.com/gohugoio/hugo", "v0.55.0"])
        assert r.returncode == 0, r.stderr
        got = lines_of(r.stdout)
        excl = "exclude github.com/chaseadamsio/goorgeous v2.0.0+incompatible"
        repl = (
            "replace github.com/markbates/inflect => "
            "github.com/markbates/inflect v0.0.0-20171215194931-a12c3aec81a6"
        )
        assert excl in got, got
        assert repl in got, got
        # a representative require line is still present and parsed
        assert "require github.com/spf13/cobra v0.0.3" in got
        # exclude and replace records follow the require records
        last_require = max(i for i, ln in enumerate(got) if ln.startswith("require "))
        assert got.index(excl) > last_require
        assert got.index(repl) > last_require


class TestMVS:
    def test_quote_build_list_transitive_not_latest(self):
        """quote's build list picks sampler v1.3.0 (not latest) plus its own dep."""
        r = run(["mvs", "rsc.io/quote", "v1.5.2"])
        assert r.returncode == 0, r.stderr
        assert lines_of(r.stdout) == [
            "golang.org/x/text v0.0.0-20170915032832-14c0d48ead0c",
            "rsc.io/sampler v1.3.0",
        ]

    def test_sampler_not_resolved_to_latest_published(self):
        """MVS never jumps sampler to the newest published v1.99.99."""
        r = run(["mvs", "rsc.io/quote", "v1.5.2"])
        got = dict(ln.split() for ln in lines_of(r.stdout))
        assert got["rsc.io/sampler"] == "v1.3.0"
        assert got["rsc.io/sampler"] != "v1.99.99"

    def test_tools_build_list_full(self):
        """x/tools resolves the whole shared-dependency graph by max-version-wins."""
        r = run(["mvs", "golang.org/x/tools", "v0.1.0"])
        assert r.returncode == 0, r.stderr
        assert lines_of(r.stdout) == [
            "github.com/yuin/goldmark v1.2.1",
            "golang.org/x/crypto v0.0.0-20200622213623-75b288015ac9",
            "golang.org/x/mod v0.3.0",
            "golang.org/x/net v0.0.0-20201021035429-f5854403a974",
            "golang.org/x/sync v0.0.0-20201020160332-67f06af15bc9",
            "golang.org/x/sys v0.0.0-20210119212857-b64e53b001e4",
            "golang.org/x/text v0.3.3",
            "golang.org/x/xerrors v0.0.0-20200804184101-5ec99f83aff1",
        ]

    def test_tools_shared_dep_takes_max(self):
        """x/text is required at v0.3.0 and v0.3.3 in the graph; the max wins."""
        r = run(["mvs", "golang.org/x/tools", "v0.1.0"])
        got = dict(ln.split() for ln in lines_of(r.stdout))
        assert got["golang.org/x/text"] == "v0.3.3"

    def test_tools_target_excluded_from_own_list(self):
        """A back-reference to x/tools does not add the target to its own list."""
        r = run(["mvs", "golang.org/x/tools", "v0.1.0"])
        assert r.returncode == 0, r.stderr
        got = dict(ln.split() for ln in lines_of(r.stdout))
        assert "golang.org/x/mod" in got
        assert "golang.org/x/tools" not in got

    def test_incompatible_pseudo_selected(self):
        """MVS carries a +incompatible pseudo-version through to the build list."""
        r = run(["mvs", "github.com/casbin/casbin", "v1.9.1"])
        assert r.returncode == 0, r.stderr
        assert lines_of(r.stdout) == [
            "github.com/Knetic/govaluate "
            "v3.0.1-0.20171022003610-9aa49832a739+incompatible",
        ]


class TestResolve:
    def test_resolve_direct_dep(self):
        """resolve returns the selected version of a direct dependency."""
        r = run(["resolve", "rsc.io/quote", "v1.5.2", "rsc.io/sampler"])
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "v1.3.0"

    def test_resolve_transitive_shared_dep(self):
        """resolve returns the max-selected version of a shared transitive dep."""
        r = run(["resolve", "golang.org/x/tools", "v0.1.0", "golang.org/x/text"])
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "v0.3.3"

    def test_resolve_absent_dep_not_found(self):
        """A dependency outside the build list prints not_found and exits non-zero."""
        r = run(["resolve", "rsc.io/quote", "v1.5.2", "rsc.io/does-not-exist"])
        assert r.returncode != 0
        assert r.stdout.strip() == "not_found"

    def test_resolve_target_path_not_found(self):
        """The target's own path is not an entry, so resolving it is not_found."""
        r = run(["resolve", "golang.org/x/tools", "v0.1.0", "golang.org/x/tools"])
        assert r.returncode != 0
        assert r.stdout.strip() == "not_found"

    def test_main_module_replace_forces_version(self):
        """A main-module replace pins markbates/inflect to its replacement
        pseudo-version, below the v1.0.0 the graph would otherwise select."""
        r = run(
            ["resolve", "github.com/gohugoio/hugo", "v0.55.0",
             "github.com/markbates/inflect"]
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "v0.0.0-20171215194931-a12c3aec81a6"
