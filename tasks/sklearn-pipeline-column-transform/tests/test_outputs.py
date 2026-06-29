from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
from conftest import BETA, BUNDLE, CORPUS, JAR
from reference_skct import REFS, assert_audit, assert_export, assert_manifest, assert_train

VF = Path(__file__).resolve().parent / "verifier_fixtures"
HIDDEN_BUNDLE = VF / "bundles/pipeline_reseed_47.json"
HIDDEN_CORPUS = VF / "feature_corpus/hidden_appendix.md"

def run(cmd, out, *, bundle=BUNDLE, corpus=CORPUS):
    out.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        ["java", "-Djava.library.path=/app/native", "-jar", JAR, cmd,
         "--bundle", str(bundle), "--corpus", str(corpus), "--out", str(out)],
        capture_output=True, text=True, timeout=300,
    )

class TestL1Ingest:
    def test_ingest_sentinel(self, tmp_path):
        proc = run("feature-ingest", tmp_path / "ing")
        assert proc.returncode == 0, proc.stderr + proc.stdout
        assert "FEATURE_INGEST_OK" in proc.stdout

    def test_manifest_oracle(self, tmp_path):
        run("feature-ingest", tmp_path / "ing")
        data = json.loads((tmp_path / "ing/feature_manifest.json").read_text())
        assert_manifest(data, REFS["alpha_manifest"])

    def test_rejects_short_corpus(self, tmp_path):
        tiny = tmp_path / "tiny.md"
        tiny.write_text("short\n", encoding="utf-8")
        proc = run("feature-ingest", tmp_path / "reject", corpus=tiny)
        assert proc.returncode != 0

    def test_beta_generalization(self, tmp_path):
        proc = run("feature-ingest", tmp_path / "beta", bundle=BETA)
        assert proc.returncode == 0, proc.stderr
        data = json.loads((tmp_path / "beta/feature_manifest.json").read_text())
        assert_manifest(data, REFS["beta_manifest"])

    def test_hidden_reseed(self, tmp_path):
        proc = run("feature-ingest", tmp_path / "hid", bundle=HIDDEN_BUNDLE, corpus=HIDDEN_CORPUS)
        assert proc.returncode == 0, proc.stderr
        data = json.loads((tmp_path / "hid/feature_manifest.json").read_text())
        assert_manifest(data, REFS["hidden_manifest"])

class TestL2Train:
    def test_train_sentinel(self, tmp_path):
        proc = run("column-transform-train", tmp_path / "train")
        assert proc.returncode == 0, proc.stderr
        assert "COLUMN_TRANSFORM_OK" in proc.stdout

    def test_train_oracle(self, tmp_path):
        run("column-transform-train", tmp_path / "train")
        data = json.loads((tmp_path / "train/transform_report.json").read_text())
        assert_train(data, REFS["alpha_train"])

    def test_beta_train(self, tmp_path):
        run("column-transform-train", tmp_path / "beta", bundle=BETA)
        data = json.loads((tmp_path / "beta/transform_report.json").read_text())
        assert_train(data, REFS["beta_train"])

    def test_hidden_train(self, tmp_path):
        run("column-transform-train", tmp_path / "hid", bundle=HIDDEN_BUNDLE, corpus=HIDDEN_CORPUS)
        data = json.loads((tmp_path / "hid/transform_report.json").read_text())
        assert_train(data, REFS["hidden_train"])

    def test_native_required(self, tmp_path):
        proc = subprocess.run(
            ["java", "-Djava.library.path=/tmp/empty", "-jar", JAR, "column-transform-train",
             "--bundle", str(BUNDLE), "--corpus", str(CORPUS), "--out", str(tmp_path / "no_native")],
            capture_output=True, text=True, timeout=300,
        )
        assert proc.returncode != 0

class TestL3Export:
    def test_export_sentinel(self, tmp_path):
        proc = run("pipeline-export", tmp_path / "export")
        assert proc.returncode == 0, proc.stderr
        assert "PIPELINE_EXPORT_OK" in proc.stdout

    def test_export_oracle(self, tmp_path):
        run("pipeline-export", tmp_path / "export")
        data = json.loads((tmp_path / "export/pipeline_registry.json").read_text())
        assert_export(data, REFS["alpha_export"])
        assert (tmp_path / "export/portable_pipeline.json").exists()

    def test_beta_export(self, tmp_path):
        run("pipeline-export", tmp_path / "beta", bundle=BETA)
        data = json.loads((tmp_path / "beta/pipeline_registry.json").read_text())
        assert_export(data, REFS["beta_export"])

    def test_hidden_export(self, tmp_path):
        run("pipeline-export", tmp_path / "hex", bundle=HIDDEN_BUNDLE, corpus=HIDDEN_CORPUS)
        data = json.loads((tmp_path / "hex/pipeline_registry.json").read_text())
        assert_export(data, REFS["hidden_export"])

class TestL4Audit:
    def test_audit_sentinel(self, tmp_path):
        run("pipeline-export", tmp_path / "export")
        proc = run("parity-audit", tmp_path / "audit")
        assert proc.returncode == 0, proc.stderr
        assert "PARITY_AUDIT_OK" in proc.stdout

    def test_audit_oracle(self, tmp_path):
        run("pipeline-export", tmp_path / "export")
        (tmp_path / "audit").mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_path / "export/portable_pipeline.json", tmp_path / "audit/portable_pipeline.json")
        run("parity-audit", tmp_path / "audit")
        data = json.loads((tmp_path / "audit/parity_audit.json").read_text())
        assert_audit(data, REFS["alpha_audit"])

    def test_hidden_audit(self, tmp_path):
        run("pipeline-export", tmp_path / "hex", bundle=HIDDEN_BUNDLE, corpus=HIDDEN_CORPUS)
        (tmp_path / "ha").mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_path / "hex/portable_pipeline.json", tmp_path / "ha/portable_pipeline.json")
        run("parity-audit", tmp_path / "ha", bundle=HIDDEN_BUNDLE, corpus=HIDDEN_CORPUS)
        data = json.loads((tmp_path / "ha/parity_audit.json").read_text())
        assert_audit(data, REFS["hidden_audit"])

class TestL5CrossArtifact:
    def test_corpus_gate(self, tmp_path):
        proc = run("feature-ingest", tmp_path / "gate")
        assert proc.returncode == 0

    def test_cross_digest_chain(self, tmp_path):
        run("pipeline-export", tmp_path / "export")
        reg = json.loads((tmp_path / "export/pipeline_registry.json").read_text())
        run("parity-audit", tmp_path / "audit")
        audit = json.loads((tmp_path / "audit/parity_audit.json").read_text())
        assert reg["export_order"] == REFS["alpha_export"]["export_order"]
        assert audit["audit_digest"] == REFS["alpha_audit"]["audit_digest"]
