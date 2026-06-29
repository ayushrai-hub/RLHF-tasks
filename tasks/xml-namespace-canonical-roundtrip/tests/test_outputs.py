import json
import os
import re
import subprocess
from pathlib import Path

import pytest

APP_DIR = Path("/app/environment")


@pytest.fixture(scope="session", autouse=True)
def install_binary():
    """Build the nsx binary from the current Go source before any artifact checks run."""
    result = subprocess.run(
        ["make", "-C", "/app/environment", "install"],
        cwd=APP_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 0, result.stdout


def run_nsx(*args, check=True):
    env = os.environ.copy()
    env["PATH"] = "/usr/local/bin:" + env.get("PATH", "")
    result = subprocess.run(
        ["nsx", *args],
        cwd=APP_DIR,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if check:
        assert result.returncode == 0, result.stdout
    return result


def write_xml(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def batch_rows(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_batch_equivalent_inputs_identical_canonical_digest(tmp_path):
    """Batch mode must assign identical canonical_sha256 to equivalent namespace inputs."""
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    a = write_xml(
        inputs / "alpha.xml",
        '<doc xmlns:p="urn:beta" xmlns:q="urn:alpha"><q:item p:rank="1" plain="yes"> same text </q:item></doc>',
    )
    b = write_xml(
        inputs / "beta.xml",
        '<doc xmlns:q="urn:alpha" xmlns:p="urn:beta"><q:item plain="yes" p:rank="1">same text</q:item></doc>',
    )
    c = write_xml(
        inputs / "gamma.xml",
        '<doc xmlns:q="urn:alpha" xmlns:p="urn:beta"><q:item p:rank="1" plain="yes">same text</q:item></doc>',
    )
    list_file = tmp_path / "batch.list"
    list_file.write_text(f"{a}\n{b}\n{c}\n", encoding="utf-8")
    batch_out = tmp_path / "batch-out"

    run_nsx("batch", "--list", str(list_file), "--out", str(batch_out))

    rows = batch_rows(batch_out / "batch.jsonl")
    assert len(rows) == 3
    digests = {row["canonical_sha256"] for row in rows}
    assert len(digests) == 1
    expected = (
        '<doc xmlns:n0="urn:alpha" xmlns:n1="urn:beta">'
        '<n0:item plain="yes" n1:rank="1">same text</n0:item></doc>\n'
    )
    for row in rows:
        canonical = (Path(row["artifact_dir"]) / "canonical.xml").read_text(
            encoding="utf-8"
        )
        assert canonical == expected
        run_nsx("replay", "--input", row["input"], "--artifact", row["artifact_dir"])


def test_batch_rerun_evicts_stale_member_directories(tmp_path):
    """A second batch run must remove member directories no longer listed."""
    first = write_xml(tmp_path / "keep.xml", '<doc xmlns="urn:a"><item>a</item></doc>')
    second = write_xml(tmp_path / "drop.xml", '<doc xmlns="urn:b"><item>b</item></doc>')
    first_list = tmp_path / "first.list"
    first_list.write_text(f"{first}\n{second}\n", encoding="utf-8")
    batch_out = tmp_path / "batch-out"
    run_nsx("batch", "--list", str(first_list), "--out", str(batch_out))
    assert (batch_out / "drop").is_dir()

    second_list = tmp_path / "second.list"
    second_list.write_text(f"{first}\n", encoding="utf-8")
    run_nsx("batch", "--list", str(second_list), "--out", str(batch_out))

    assert (batch_out / "keep").is_dir()
    assert not (batch_out / "drop").exists()
    rows = batch_rows(batch_out / "batch.jsonl")
    assert len(rows) == 1
    assert rows[0]["input"] == str(first)


def test_attribute_only_namespace_prefix_order(tmp_path):
    """Namespace URIs used only on attributes must still receive lexicographic n-prefixes."""
    xml = write_xml(
        tmp_path / "attr-only.xml",
        '<root plain="yes" xmlns:a="urn:zebra" a:flag="1" xmlns:b="urn:alpha" b:flag="2"/>',
    )
    out = tmp_path / "attr-only-out"
    run_nsx("build", "--input", str(xml), "--out", str(out))

    canonical = (out / "canonical.xml").read_text(encoding="utf-8")
    assert (
        canonical
        == '<root xmlns:n0="urn:alpha" xmlns:n1="urn:zebra" plain="yes" n0:flag="2" n1:flag="1"/>\n'
    )
    scope = read_json(out / "scope.json")
    assert scope["namespace_uris"] == ["urn:alpha", "urn:zebra"]
    run_nsx("replay", "--input", str(xml), "--artifact", str(out))


def test_prefix_rebinding_sibling_isolation_and_replay(tmp_path):
    """Inner prefix rebinding must not mutate outer scope for following siblings."""
    xml = write_xml(
        tmp_path / "rebind.xml",
        '<root xmlns:a="urn:outer"><mid xmlns:a="urn:inner"><a:leaf/></mid><after><a:peer/></after></root>',
    )
    out = tmp_path / "rebind-out"
    run_nsx("build", "--input", str(xml), "--out", str(out))

    canonical = (out / "canonical.xml").read_text(encoding="utf-8")
    assert (
        canonical
        == '<root xmlns:n0="urn:inner" xmlns:n1="urn:outer"><mid><n0:leaf/></mid><after><n1:peer/></after></root>\n'
    )
    scope = read_json(out / "scope.json")
    peer = next(node for node in scope["nodes"] if node["name"]["local"] == "peer")
    assert peer["name"]["uri"] == "urn:outer"
    run_nsx("replay", "--input", str(xml), "--artifact", str(out))


def test_scope_declared_bindings_are_element_local(tmp_path):
    """scope.nodes[].declared must list only declarations on that element."""
    xml = write_xml(
        tmp_path / "declared.xml",
        '<root xmlns:a="urn:outer"><child xmlns:a="urn:inner"/></root>',
    )
    out = tmp_path / "declared-out"
    run_nsx("build", "--input", str(xml), "--out", str(out))

    scope = read_json(out / "scope.json")
    child = next(node for node in scope["nodes"] if node["name"]["local"] == "child")
    assert child["declared"] == [{"prefix": "a", "uri": "urn:inner"}]
    run_nsx("validate", "--input", str(xml), "--artifact", str(out))


def test_deep_default_reset_sibling_isolation(tmp_path):
    """Nested default-namespace reset must not leak cleared bindings to later siblings."""
    xml = write_xml(
        tmp_path / "deep-reset.xml",
        '<root xmlns="urn:a"><mid xmlns="urn:b"><leaf/></mid><mid xmlns="" id="local"><item/></mid><tail id="t"/></root>',
    )
    out = tmp_path / "deep-reset-out"
    run_nsx("build", "--input", str(xml), "--out", str(out))

    canonical = (out / "canonical.xml").read_text(encoding="utf-8")
    assert (
        canonical
        == '<n0:root xmlns:n0="urn:a" xmlns:n1="urn:b"><n1:mid><n1:leaf/></n1:mid><mid id="local"><item/></mid><n0:tail id="t"/></n0:root>\n'
    )
    scope = read_json(out / "scope.json")
    reset_mid = next(
        node for node in scope["nodes"] if node["name"]["local"] == "mid" and node["name"]["uri"] == ""
    )
    assert reset_mid["declared"] == [{"prefix": "", "uri": ""}]
    tail = next(node for node in scope["nodes"] if node["name"]["local"] == "tail")
    assert tail["name"]["uri"] == "urn:a"
    run_nsx("replay", "--input", str(xml), "--artifact", str(out))


def test_default_namespace_reset_scope_artifacts_and_cleanup(tmp_path):
    """Default namespace reset must clear element namespaces while preserving qualified attributes."""
    reset_source = (
        '<r xmlns="urn:outer" xmlns:o="urn:outer" xmlns:x="urn:x" id="root">'
        '<section xmlns="" id="local" o:id="outer" x:code="A"><leaf /></section></r>'
    )
    reset_local = re.search(
        r"<([A-Za-z][A-Za-z0-9_-]*) xmlns=\"\"", reset_source
    ).group(1)
    leaf_local = re.search(r"<([A-Za-z][A-Za-z0-9_-]*) />", reset_source).group(1)
    xml = write_xml(tmp_path / "reset.xml", reset_source)
    out = tmp_path / "reset-out"
    out.mkdir()
    (out / "scope.json.tmp").write_text("stale", encoding="utf-8")

    run_nsx("build", "--input", str(xml), "--out", str(out))

    canonical = (out / "canonical.xml").read_text(encoding="utf-8")
    assert "n0:section" not in canonical
    assert (
        '<section id="local" n0:id="outer" n1:code="A"><leaf/></section>' in canonical
    )
    assert len(list(out.glob("*.tmp"))) == 0

    scope = read_json(out / "scope.json")
    assert scope["namespace_uris"] == ["urn:outer", "urn:x"]
    section = next(
        entry for entry in scope["nodes"] if entry["name"]["local"] == reset_local
    )
    leaf = next(
        entry for entry in scope["nodes"] if entry["name"]["local"] == leaf_local
    )
    assert section["name"]["uri"] == ""
    assert leaf["name"]["uri"] == ""
    assert section["declared"] == [{"prefix": "", "uri": ""}]
    run_nsx("validate", "--input", str(xml), "--artifact", str(out))
    run_nsx("replay", "--input", str(xml), "--artifact", str(out))


def test_unprefixed_attributes_remain_local_under_default_namespace(tmp_path):
    """Unprefixed attributes under a default namespace must remain local."""
    xml = write_xml(
        tmp_path / "local-attr.xml",
        '<r xmlns="urn:x" xmlns:x="urn:x" id="plain" x:id="qualified"><child xmlns="" id="c" /></r>',
    )
    out = tmp_path / "local-out"
    run_nsx("build", "--input", str(xml), "--out", str(out))

    canonical = (out / "canonical.xml").read_text(encoding="utf-8")
    assert (
        canonical
        == '<n0:r xmlns:n0="urn:x" id="plain" n0:id="qualified"><child id="c"/></n0:r>\n'
    )
    scope = read_json(out / "scope.json")
    root_attrs = {
        (a["uri"], a["local"], a["value"]) for a in scope["nodes"][0]["attributes"]
    }
    assert ("", "id", "plain") in root_attrs
    assert ("urn:x", "id", "qualified") in root_attrs
    run_nsx("validate", "--input", str(xml), "--artifact", str(out))


def test_multi_run_output_directory_replaces_prior_artifacts(tmp_path):
    """Reusing an output directory for a new input must replace artifacts and the input marker."""
    first = write_xml(tmp_path / "first.xml", '<doc xmlns="urn:a"><item>a</item></doc>')
    second = write_xml(
        tmp_path / "second.xml", '<doc xmlns="urn:b"><item>b</item></doc>'
    )
    out = tmp_path / "shared-out"
    out.mkdir()
    (out / "canonical.xml.tmp").write_text("stale", encoding="utf-8")
    (out / ".nsx-input").write_text("/stale/path\n", encoding="utf-8")

    run_nsx("build", "--input", str(first), "--out", str(out))
    run_nsx("build", "--input", str(second), "--out", str(out))

    scope = read_json(out / "scope.json")
    assert scope["input"] == str(second)
    assert scope["namespace_uris"] == ["urn:b"]
    assert (out / ".nsx-input").read_text(encoding="utf-8").strip() == str(second)
    assert len(list(out.glob("*.tmp"))) == 0
    run_nsx("replay", "--input", str(second), "--artifact", str(out))


def test_ambiguous_attributes_are_rejected(tmp_path):
    """Two attributes with the same expanded namespace URI and local name must not be accepted."""
    xml = write_xml(
        tmp_path / "ambiguous.xml",
        '<r xmlns:a="urn:z" xmlns:b="urn:z" a:id="1" b:id="2" />',
    )
    out = tmp_path / "ambiguous-out"
    result = run_nsx("build", "--input", str(xml), "--out", str(out), check=False)
    assert result.returncode != 0
    assert "duplicate attribute expanded name" in result.stdout
